# coding: utf-8

import re
import os
import time
import tmt
import click
import requests
import fmf

from tmt.utils import ProvisionError, WORKDIR_ROOT, retry_session

def import_testcloud():
    """
    Import testcloud module only when needed

    Until we have a separate package for each plugin.
    """
    global testcloud
    try:
        import testcloud.image
        import testcloud.instance
    except ImportError:
        raise ProvisionError(
            "Install 'testcloud' to provision using this method.")

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
    <emulator>{{ emulator_path }}</emulator>
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

# VM defaults
DEFAULT_BOOT_TIMEOUT = 60      # seconds
DEFAULT_CONNECT_TIMEOUT = 60   # seconds

# Image guessing related variables
KOJI_URL = 'https://kojipkgs.fedoraproject.org/compose'


class ProvisionTestcloud(tmt.steps.provision.ProvisionPlugin):
    """
    Local virtual machine using testcloud

    Minimal config which uses the latest fedora image:

        provision:
            how: virtual

    Here's a full config example:

        provision:
            how: virtual
            image: fedora
            user: root
            memory: 2048

    As the image use 'fedora' for the latest released Fedora compose,
    'rawhide' for the latest Rawhide compose, short aliases such as
    'fedora-32', 'f-32' or 'f32' for specific release or a full url to
    the qcow2 image for example from:

        https://kojipkgs.fedoraproject.org/compose/

    Use full path for image stored on local disk, for example:

        /var/tmp/images/Fedora-Cloud-Base-31-1.9.x86_64.qcow2
    """

    # Guest instance
    _guest = None

    # Supported methods
    _methods = [
        tmt.steps.Method(name='virtual.testcloud', doc=__doc__, order=50),
        ]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for testcloud """
        return [
            click.option(
                '-i', '--image', metavar='IMAGE',
                help='Select image to use. Short name or complete url.'),
            click.option(
                '-m', '--memory', metavar='MEMORY',
                help='Set available memory in MB, 2048 MB by default.'),
            click.option(
                '-D', '--disk', metavar='MEMORY',
                help='Specify disk size in GB, 10 GB by default.'),
            click.option(
                '-u', '--user', metavar='USER',
                help='Username to use for all guest operations.'),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        defaults = {
            'user': 'root',
            'memory': 2048,
            'disk': 10,
            'image': 'fedora',
            }
        if option in defaults:
            return defaults[option]
        return default

    def show(self):
        """ Show provision details """
        super().show(['image', 'user', 'memory', 'disk'])

    def wake(self, data=None):
        """ Override options and wake up the guest """
        super().wake(['image', 'memory', 'disk', 'user'])

        # Convert memory and disk to integers
        for key in ['memory', 'disk']:
            if isinstance(self.get(key), str):
                self.data[key] = int(self.data[key])

        # Wake up testcloud instance
        if data:
            guest = GuestTestcloud(data, name=self.name, parent=self.step)
            guest.wake()
            self._guest = guest

    def go(self):
        """ Provision the testcloud instance """
        super().go()

        # Give info about provided data
        data = dict()
        for key in ['image', 'user', 'memory', 'disk']:
            data[key] = self.get(key)
            if key == 'memory':
                self.info('memory', f"{self.get('memory')} MB", 'green')
            elif key == 'disk':
                self.info('disk', f"{self.get('disk')} GB", 'green')
            else:
                self.info(key, data[key], 'green')

        # Create a new GuestTestcloud instance and start it
        self._guest = GuestTestcloud(data, name=self.name, parent=self.step)
        self._guest.start()

    def guest(self):
        """ Return the provisioned guest """
        return self._guest


class GuestTestcloud(tmt.Guest):
    """
    Testcloud Instance

    The following keys are expected in the 'data' dictionary::

        image ...... qcov image name or url
        user ....... user name to log in
        memory ..... memory size for vm
        disk ....... disk size for vm
    """

    def _get_url(self, url, message):
        """ Get url, retry when fails, return response """
        timeout = DEFAULT_CONNECT_TIMEOUT
        wait = 1
        while True:
            try:
                response = retry_session().get(url)
                if response.ok:
                    return response
            except requests.RequestException:
                pass
            if timeout < 0:
                raise ProvisionError(
                    f'Failed to {message} in {DEFAULT_CONNECT_TIMEOUT}s.')
            self.debug(
                f'Unable to {message} ({url}), retrying, '
                f'{fmf.utils.listed(timeout, "second")} left.')
            time.sleep(wait)
            wait += 1
            timeout -= wait

    def _guess_image_url(self, name):
        """ Guess image url for given name """

        def latest_release():
            """ Get the latest released Fedora number """
            try:
                response = self._get_url(KOJI_URL, 'check Fedora composes')
                releases = re.findall(r'>(\d\d)/<', response.text)
                return releases[-1]
            except IndexError:
                raise ProvisionError(
                    f"Latest Fedora release not found at '{KOJI_URL}'.")

        # Try to check if given url is a local file
        if os.path.exists(name):
            return f'file://{name}'

        # Map fedora aliases (e.g. rawhide, fedora, fedora-32, f-32, f32)
        name = name.lower().strip()
        matched = re.match(r'^f(edora)?-?(\d+)$', name)
        if matched:
            release = matched.group(2)
        elif 'rawhide' in name:
            release = 'rawhide'
        elif name == 'fedora':
            release = latest_release()
        else:
            raise ProvisionError(f"Could not map '{name}' to compose.")

        # Prepare the full qcow name
        images = f"{KOJI_URL}/{release}/latest-Fedora-{release.capitalize()}"
        images += "/compose/Cloud/x86_64/images"
        response = self._get_url(images, 'get the full qcow name')
        matched = re.search(">(Fedora-Cloud[^<]*qcow2)<", response.text)
        try:
            compose_name = matched.group(1)
        except AttributeError:
            raise ProvisionError(
                f"Failed to detect full compose name from '{images}'.")
        return f'{images}/{compose_name}'


    @staticmethod
    def _create_template():
        """ Create libvirt domain template if it does not exist """
        if os.path.exists(DOMAIN_TEMPLATE_FILE):
            return
        with open(DOMAIN_TEMPLATE_FILE, 'w') as template:
            template.write(DOMAIN_TEMPLATE)

    def load(self, data):
        """ Load guest data and initialize attributes """
        super().load(data)
        self.image = None
        self.image_url = data.get('image')
        self.instance = None
        self.instance_name = data.get('instance')
        self.memory = data.get('memory')
        self.disk = data.get('disk')

    def save(self):
        """ Save guest data for future wake up """
        data = super().save()
        data['instance'] = self.instance_name
        data['image'] = self.image_url
        return data

    def wake(self):
        """ Wake up the guest """
        self.debug(
            f"Waking up testcloud instance '{self.instance_name}'.",
            level=2, shift=0)
        self.prepare_config()
        self.image = testcloud.image.Image(self.image_url)
        self.instance = testcloud.instance.Instance(
            self.instance_name, image=self.image)

    def prepare_ssh_key(self):
        """ Prepare ssh key for authentication """
        # Create ssh key paths
        self.key = os.path.join(self.workdir, 'id_rsa')
        self.pubkey = os.path.join(self.workdir, 'id_rsa.pub')

        # Generate ssh key
        self.debug('Generating an ssh key.')
        self.run(f'ssh-keygen -f {self.key} -N ""')
        with open(self.pubkey, 'r') as pubkey:
            self.config.USER_DATA = USER_DATA.format(
                user_name=self.user, public_key=pubkey.read())

    def prepare_config(self):
        """ Prepare common configuration """
        import_testcloud()

        # Get configuration
        self.config = testcloud.config.get_config()

        # Make sure download progress is disabled unless in debug mode,
        # so it does not spoil our logging
        self.config.DOWNLOAD_PROGRESS = self.opt('debug') > 2

        # Configure to tmt's storage directories
        self.config.DATA_DIR = TESTCLOUD_DATA
        self.config.STORE_DIR = TESTCLOUD_IMAGES

    def start(self):
        """ Start provisioned guest """
        if self.opt('dry'):
            return
        # Make sure required directories exist
        os.makedirs(TESTCLOUD_DATA, exist_ok=True)
        os.makedirs(TESTCLOUD_IMAGES, exist_ok=True)

        # Make sure libvirt domain template exists
        GuestTestcloud._create_template()

        # Prepare config
        self.prepare_config()

        # If image does not start with http/https/file, consider it a
        # mapping value and try to guess the URL
        if not re.match(r'^(?:https?|file)://.*', self.image_url):
            self.image_url = self._guess_image_url(self.image_url)

        # Initialize and prepare testcloud image
        self.image = testcloud.image.Image(self.image_url)
        self.verbose('qcow', self.image.name, 'green')
        if not os.path.exists(self.image.local_path):
            self.info('progress', 'downloading...', 'cyan')
        try:
            self.image.prepare()
        except FileNotFoundError:
            raise ProvisionError(f"Image '{self.image.local_path}' not found.")
        except testcloud.exceptions.TestcloudPermissionsError:
            raise ProvisionError(
                f"Failed to prepare the image. "
                f"Check the '{TESTCLOUD_IMAGES}' directory permissions.")

        # Create instance
        self.instance_name = self._random_name()
        self.instance = testcloud.instance.Instance(
            name=self.instance_name, image=self.image)
        self.verbose('name', self.instance_name, 'green')

        # Prepare ssh key
        self.prepare_ssh_key()

        # Boot the virtual machine
        self.info('progress', 'booting...', 'cyan')
        self.instance.ram = self.memory
        self.instance.disk_size = self.disk
        self.instance.prepare()
        self.instance.spawn_vm()
        try:
            self.instance.start(DEFAULT_BOOT_TIMEOUT)
        except testcloud.exceptions.TestcloudInstanceError as error:
            raise ProvisionError(
                f'Failed to boot testcloud instance ({error}).')
        self.guest = self.instance.get_ip()
        self.instance.create_ip_file(self.guest)

        # Wait a bit until the box is up
        timeout = DEFAULT_CONNECT_TIMEOUT
        wait = 1
        while True:
            try:
                self.execute('whoami')
                break
            except tmt.utils.RunError:
                if timeout < 0:
                    raise ProvisionError(
                        f'Failed to connect in {DEFAULT_CONNECT_TIMEOUT}s.')
                self.debug(
                    f'Failed to connect to machine, retrying, '
                    f'{fmf.utils.listed(timeout, "second")} left.')
            time.sleep(wait)
            wait += 1
            timeout -= wait

    def stop(self):
        """ Stop provisioned guest """
        if self.instance:
            self.debug(f"Stopping testcloud instance '{self.instance_name}'.")
            try:
                self.instance.stop()
            except testcloud.exceptions.TestcloudInstanceError as error:
                raise tmt.utils.ProvisionError(
                    f"Failed to stop testcloud instance: {error}")
            self.info('guest', 'stopped', 'green')

    def remove(self):
        """ Remove the guest (disk cleanup) """
        if self.instance:
            self.debug(f"Removing testcloud instance '{self.instance_name}'.")
            try:
                self.instance.remove(autostop=True)
            except FileNotFoundError as error:
                raise tmt.utils.ProvisionError(
                    f"Failed to remove testcloud instance: {error}")
            self.info('guest', 'removed', 'green')
