import re
import os
import time

import requests

from tmt.steps.provision.base import ProvisionBase
from tmt.utils import GeneralError, SpecificationError, WORKDIR_ROOT
from tmt.utils import shell_variables

# Testcloud cache to our tmt's workdir root
TESTCLOUD_DATA = os.path.join(WORKDIR_ROOT, 'testcloud')
TESTCLOUD_IMAGES = os.path.join(TESTCLOUD_DATA, 'images')

# Userdata for cloud-init
USER_DATA = """#cloud-config
password: %s
chpasswd:
  expire: false
users:
  - default
  - name: {user_name}
ssh_authorized_keys:
  - {public_key}
ssh_pwauth: true
disable_root: false
runcmd:
  - sed -i -e '/^.*PermitRootLogin/s/^.*$/PermitRootLogin yes/'
    /etc/ssh/sshd_config
  - systemctl reload sshd
"""

# Libvirt domain XML template related variables
DOMAIN_TEMPLATE_NAME = 'domain-template.jinja'
DOMAIN_TEMPLATE_FILE = os.path.join(TESTCLOUD_DATA, DOMAIN_TEMPLATE_NAME)
DOMAIN_TEMPLATE = """<domain type='kvm'>
    <name>{{ domain_name }}</name>
    <uuid>{{ uuid }}</uuid>
    <memory unit='KiB'>{{ memory }}</memory>
    <currentMemory unit='KiB'>{{ memory }}</currentMemory>
  <vcpu placement='static'>1</vcpu>
  <os>
    <type arch='x86_64' machine='pc'>hvm</type>
    {{ uefi_loader }}
    <boot dev='hd'/>
  </os>
  <features>
    <acpi/>
    <apic/>
    <vmport state='off'/>
  </features>
  <cpu mode='host-passthrough'/>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <pm>
    <suspend-to-mem enabled='no'/>
    <suspend-to-disk enabled='no'/>
  </pm>
  <devices>
    <emulator>/usr/bin/qemu-kvm</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2'/>
      <source file="{{ disk }}"/>
      <target dev='vda' bus='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
    </disk>
    <disk type='file' device='disk'>
      <driver name='qemu' type='raw' cache='unsafe'/>
      <source file="{{ seed }}"/>
      <target dev='vdb' bus='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x08' function='0x0'/>
    </disk>
    <interface type='network'>
        <mac address="{{ mac_address }}"/>
      <source network='default'/>
      <model type='rtl8139'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
    <input type='keyboard' bus='ps2'/>
    <memballoon model='virtio'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x09' function='0x0'/>
    </memballoon>
    <rng model='virtio'>
      <backend model='random'>/dev/urandom</backend>
    </rng>
  </devices>
</domain>
"""

# Default image
DEFAULT_IMAGE = 'fedora'

# VM defaults
DEFAULT_MEMORY = 2048      # MiB
DEFAULT_DISK_SIZE = 10     # GiB
DEFAULT_USER = 'root'
DEFAULT_BOOT_TIMEOUT = 60  # seconds
DEFAULT_SSH_CONNECT_TIMEOUT = 60  # seconds

# Image guessing related variables
KOJI_URL = 'https://kojipkgs.fedoraproject.org/compose'

RAWHIDE_URL = f'{KOJI_URL}/rawhide/latest-Fedora-Rawhide'
RAWHIDE_ID = f'{RAWHIDE_URL}/COMPOSE_ID'
RAWHIDE_IMAGE_URL = f'{RAWHIDE_URL}/compose/Cloud/x86_64/images'


def guess_image_url(name):
    """ Guess image url for given name """

    def get_compose_id(compose_id_url):
        response = requests.get(f'{compose_id_url}')

        if not response:
            raise GeneralError(
                f'Failed to find compose ID for '
                f"'{name}' at '{compose_id_url}'")

        return response.text

    # map fedora, rawhide or fedora-rawhide to latest rawhide image
    if re.match(r'^(fedora|fedora-rawhide|rawhide)$', name, re.IGNORECASE):
        compose_id = get_compose_id(RAWHIDE_ID)
        compose_name = compose_id.replace(
            'Fedora-Rawhide', 'Fedora-Cloud-Base-Rawhide')
        return f'{RAWHIDE_IMAGE_URL}/{compose_name}.x86_64.qcow2'

    # Try to check if given url is a local file
    if os.path.exists(name):
        return f'file://{name}'

    raise GeneralError(f"Could not map '{name}' to compose.")


class ProvisionTestcloud(ProvisionBase):
    """ Testcloud Provisioner """
    def __init__(self, data, step):
        super(ProvisionTestcloud, self).__init__(data, step)

        self._prepare_map = {
            'ansible': self._prepare_ansible,
            'shell': self._prepare_shell,
        }

        # Initialize testcloud image
        self.image = None

        # Testcloud instance and ip
        self.instance = None
        self.ip = None

        # Default user
        self.user = self.option('user') or DEFAULT_USER

        # Create ssh key
        self.ssh_key = os.path.join(self.provision_dir, 'id_rsa')
        self.ssh_pubkey = os.path.join(self.provision_dir, 'id_rsa.pub')

        # Common ssh args
        self.ssh_args = [
            '-i', self.ssh_key,
            '-oStrictHostKeyChecking=no',
            '-oUserKnownHostsFile=/dev/null',
            ]
        self.ssh_args_shell = self.join(self.ssh_args)

        # Connection host
        self.ssh_user_host = None

        # Shell compatible environment variables, so they can be correctly
        # passed to ssh's shell. Needs to be prepended with export and run
        # as a separate command.
        self.shell_env = ''
        if self.opt('environment'):
            env = ' '.join(shell_variables(self.opt('environment')))
            self.shell_env = f'export {env};'

        # Make sure required directories exist
        os.makedirs(TESTCLOUD_DATA, exist_ok=True)
        os.makedirs(TESTCLOUD_IMAGES, exist_ok=True)

        # Make sure libvirt domain template exists
        ProvisionTestcloud._create_template()

    def option(self, key):
        """ Return option specified on command line """
        # Consider command line as priority
        if self.opt(key):
            return self.opt(key)

        return self.data.get(key, None)

    @staticmethod
    def _create_template():
        """ Create libvirt domain template if it does not exist """
        if os.path.exists(DOMAIN_TEMPLATE_FILE):
            return

        with open(DOMAIN_TEMPLATE_FILE, 'w') as template:
            template.write(DOMAIN_TEMPLATE)

    def go(self):
        super(ProvisionTestcloud, self).go()

        # If image does not start with http/https/file, consider it a mapping
        # value and try to guess the URL
        image_url = self.option('image') or DEFAULT_IMAGE
        if not re.match(r'^(?:https?|file)://.*', image_url):
            image_url = guess_image_url(image_url)

        # Import testcloud module only when needed (until we have a
        # separate package for each plugin)
        try:
            import testcloud.image
            import testcloud.instance
        except ImportError:
            raise GeneralError(
                "Install 'testcloud' to provision using this method.")

        # Get configuration
        config = testcloud.config.get_config()

        # Make sure download progress is disabled, so it
        # does not spoil our logging
        config.DOWNLOAD_PROGRESS = False

        # Configure to tmt's storage directories
        config.DATA_DIR = TESTCLOUD_DATA
        config.STORE_DIR = TESTCLOUD_IMAGES

        # Initialize testcloud image
        self.image = testcloud.image.Image(image_url)

        # Show which image we are using
        self.info('image', f'{self.image.name}', 'green')

        status = f'{self.image.name}'
        if not os.path.exists(self.image.local_path):
            self.info('status', 'downloading', 'green')

        # prepare testcloud image
        try:
            self.image.prepare()
        except FileNotFoundError:
            raise GeneralError(
                f"Could not find image '{self.image.local_path}'")

        self.instance = testcloud.instance.Instance(
            self.instance_name, image=self.image)

        # generate ssh key
        self.run(f'ssh-keygen -f {self.ssh_key} -N ""')

        with open(self.ssh_pubkey, 'r') as pubkey:
            config.USER_DATA = USER_DATA.format(
                user_name=self.user, public_key=pubkey.read())

        self.info('status', 'booting', 'green')
        self.instance.ram = self.option('memory') or DEFAULT_MEMORY
        self.instance.disk_size = DEFAULT_DISK_SIZE
        self.instance.prepare()
        self.instance.spawn_vm()

        try:
            self.instance.start(DEFAULT_BOOT_TIMEOUT)
        except testcloud.exceptions.TestcloudInstanceError:
            # TODO: find out how to get detailed information about boot problem
            raise GeneralError('Failed to boot instance')

        self.ip = self.instance.get_ip()
        self.instance.create_ip_file(self.ip)
        self.ssh_user_host = f'{self.user}@{self.instance.get_ip()}'

        for i in range(1, DEFAULT_SSH_CONNECT_TIMEOUT):
            try:
                self.execute('whoami')
                break
            except GeneralError:
                self.debug('failed to connect to machine, retrying')
            time.sleep(1)

        if i == DEFAULT_BOOT_TIMEOUT:
            raise GeneralError(
                'Failed to login to the machine in {DEFAULT_BOOT_TIMEOUT}s')

        self.info('instance', self.ssh_user_host, 'green')

    def execute(self, *args, **kwargs):
        if not self.instance:
            raise GeneralError(
                'Could not execute without a provisioned VM.')

        return self.run(
            ['ssh'] + self.ssh_args + [self.ssh_user_host] +
            [f'{self.shell_env} {self.join(args)}'], shell=False)[0].rstrip()

    def _prepare_ansible(self, what):
        """ Prepare using ansible """
        # Playbook paths should be relative to the metadata tree root
        playbook = os.path.join(self.step.plan.run.tree.root, what)
        # Set collumns to 80 characters while running ansible
        self.run(
            f'stty cols 80; ansible-playbook '
            f'--ssh-common-args="{self.ssh_args_shell}" '
            f'-e ansible_python_interpreter=auto '
            f'-v -i {self.user}@{self.ip}, {playbook}')

    def _prepare_shell(self, what):
        """ Prepare using shell """
        # Set current working directory to the test metadata root
        self.execute(what, cwd=self.step.plan.run.tree.root)

    def prepare(self, how, what):
        """ Run prepare phase """
        try:
            self._prepare_map[how](what)
        except AttributeError as e:
            raise SpecificationError(
                f"Prepare method '{how}' is not supported.")

    def sync_workdir_to_guest(self):
        """ sync on demand """
        self.run(
            f'rsync -Rrze "ssh {self.ssh_args_shell}" '
            f'{self.step.plan.workdir} {self.user}@{self.ip}:/')

    def sync_workdir_from_guest(self):
        """ sync from guest to host """
        self.run(
            f'rsync -Rrze "ssh {self.ssh_args_shell}" '
            f'{self.user}@{self.ip}:{self.step.plan.workdir} /')

    def destroy(self):
        """ Remove the container """
        if self.instance:
            self.info('instance', 'stopping', 'green')
            self.instance.stop()
