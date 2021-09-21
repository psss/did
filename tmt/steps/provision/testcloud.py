# coding: utf-8

import os
import re
import time

import click
import fmf
import requests

import tmt
from tmt.steps.provision import ProvisionPlugin
from tmt.utils import WORKDIR_ROOT, ProvisionError, retry_session


def import_testcloud():
    """
    Import testcloud module only when needed

    Until we have a separate package for each plugin.
    """
    global testcloud
    global libvirt
    try:
        import libvirt
        import testcloud.image
        import testcloud.instance
        import testcloud.util
    except ImportError:
        raise ProvisionError(
            "Install 'testcloud' to provision using this method.")


# Testcloud cache to our tmt's workdir root
TESTCLOUD_DATA = os.path.join(WORKDIR_ROOT, 'testcloud')
TESTCLOUD_IMAGES = os.path.join(TESTCLOUD_DATA, 'images')

# Userdata for cloud-init
USER_DATA = """#cloud-config
chpasswd:
  list: |
    {user_name}:%s
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
    -e '/^.*UseDNS/s/^.*$/UseDNS no/'
    -e '/^.*GSSAPIAuthentication/s/^.*$/GSSAPIAuthentication no/'
    /etc/ssh/sshd_config
  - systemctl reload sshd
  - [sh, -c, 'if [ ! -f /etc/systemd/network/20-tc-usernet.network ] &&
  systemctl status systemd-networkd | grep -q "enabled;\\svendor\\spreset:\\senabled";
  then mkdir -p /etc/systemd/network/ &&
  echo "[Match]" >> /etc/systemd/network/20-tc-usernet.network &&
  echo "Name=en*" >> /etc/systemd/network/20-tc-usernet.network &&
  echo "[Network]" >> /etc/systemd/network/20-tc-usernet.network &&
  echo "DHCP=yes" >> /etc/systemd/network/20-tc-usernet.network; fi']
  - [sh, -c, 'if systemctl status systemd-networkd |
  grep -q "enabled;\\svendor\\spreset:\\senabled"; then
  systemctl restart systemd-networkd; fi']
  - [sh, -c, 'if cat /etc/os-release |
  grep -q platform:el8; then systemctl restart sshd; fi']
"""

# Libvirt domain XML template related variables
DOMAIN_TEMPLATE_NAME = 'domain-template.jinja'
DOMAIN_TEMPLATE_FILE = os.path.join(TESTCLOUD_DATA, DOMAIN_TEMPLATE_NAME)
DOMAIN_TEMPLATE = """<domain type='kvm' xmlns:qemu='http://libvirt.org/schemas/domain/qemu/1.0'>
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
      <driver name='qemu' type='qcow2' cache='unsafe'/>
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
    <interface type='{{ network_type }}'>
      <mac address="{{ mac_address }}"/>
      {{ network_source }}
      {{ ip_setup }}
      <model type='virtio'/>
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
  {{ qemu_args }}
</domain>
"""

# VM defaults
DEFAULT_BOOT_TIMEOUT = 60      # seconds
DEFAULT_CONNECT_TIMEOUT = 60   # seconds

# SSH key type, set None for ssh-keygen default one
SSH_KEYGEN_TYPE = "ecdsa"


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

    Short names are also provided for 'centos', 'centos-stream',
    'debian' and 'ubuntu' (e.g. 'centos-8' or 'c8').

    Use the full path for images stored on local disk, for example:

        /var/tmp/images/Fedora-Cloud-Base-31-1.9.x86_64.qcow2

    In addition to the qcow2 format, vagrant boxes can be used as well,
    testcloud will take care of unpacking the image for you.
    """

    # Guest instance
    _guest = None

    # Supported methods
    _methods = [
        tmt.steps.Method(name='virtual.testcloud', doc=__doc__, order=50),
        ]

    # Supported keys
    _keys = ["image", "user", "memory", "disk", "connection"]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for testcloud """
        return [
            click.option(
                '-i', '--image', metavar='IMAGE',
                help='Select image to be used. Provide a short name, '
                     'full path to a local file or a complete url.'),
            click.option(
                '-m', '--memory', metavar='MEMORY',
                help='Set available memory in MB, 2048 MB by default.'),
            click.option(
                '-D', '--disk', metavar='MEMORY',
                help='Specify disk size in GB, 10 GB by default.'),
            click.option(
                '-u', '--user', metavar='USER',
                help='Username to use for all guest operations.'),
            click.option(
                '-c', '--connection',
                type=click.Choice(['session', 'system']),
                help="What session type to use, 'session' by default."),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        defaults = {
            'user': 'root',
            'memory': 2048,
            'disk': 10,
            'image': 'fedora',
            'connection': 'session',
            }
        if option in defaults:
            return defaults[option]
        return default

    def wake(self, keys=None, data=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys, data=data)

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
        for key in self._keys + self._common_keys:
            data[key] = self.get(key)
            if key == 'memory':
                self.info('memory', f"{self.get('memory')} MB", 'green')
            elif key == 'disk':
                self.info('disk', f"{self.get('disk')} GB", 'green')
            elif key == 'connection':
                self.verbose(key, data[key], 'green')
            else:
                if data[key] is not None:
                    self.info(key, data[key], 'green')

        # Create a new GuestTestcloud instance and start it
        self._guest = GuestTestcloud(data, name=self.name, parent=self.step)
        self._guest.start()

    def guest(self):
        """ Return the provisioned guest """
        return self._guest

    @classmethod
    def clean_images(cls, clean, dry):
        """ Remove the testcloud images """
        clean.info('testcloud', shift=1, color='green')
        if not os.path.exists(TESTCLOUD_IMAGES):
            clean.warn(
                f"Directory '{TESTCLOUD_IMAGES}' does not exist.", shift=2)
            return
        for image in os.listdir(TESTCLOUD_IMAGES):
            image = os.path.join(TESTCLOUD_IMAGES, image)
            if dry:
                clean.verbose(f"Would remove '{image}'.", shift=2)
            else:
                clean.verbose(f"Removing '{image}'.", shift=2)
                os.remove(image)


class GuestTestcloud(tmt.Guest):
    """
    Testcloud Instance

    The following keys are expected in the 'data' dictionary::

        image ...... qcov image name or url
        user ....... user name to log in
        memory ..... memory size for vm
        disk ....... disk size for vm
        connection . either session (default) or system, to be passed to qemu
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

        # Try to check if given url is a local file
        if os.path.isabs(name) and os.path.isfile(name):
            return f'file://{name}'

        name = name.lower().strip()
        url = None

        # Map fedora aliases (e.g. rawhide, fedora, fedora-32, f-32, f32)
        matched_fedora = re.match(r'^f(edora)?-?(\d+)$', name)
        # Map centos aliases (e.g. centos:X, centos, centos-stream:X)
        matched_centos = [re.match(r'^c(entos)?-?(\d+)$', name),
                          re.match(r'^c(entos-stream)?-?(\d+)$', name)]
        matched_ubuntu = re.match(r'^u(buntu)?-?(\w+)$', name)
        matched_debian = re.match(r'^d(ebian)?-?(\w+)$', name)

        # Plain name match means we want the latest release
        if name == 'fedora':
            url = testcloud.util.get_fedora_image_url("latest")
        elif name == 'centos':
            url = testcloud.util.get_centos_image_url("latest")
        elif name == 'centos-stream':
            url = testcloud.util.get_centos_image_url(
                "latest", stream=True)
        elif name == 'ubuntu':
            url = testcloud.util.get_ubuntu_image_url("latest")
        elif name == 'debian':
            url = testcloud.util.get_debian_image_url("latest")

        elif matched_fedora:
            url = testcloud.util.get_fedora_image_url(matched_fedora.group(2))
        elif matched_centos[0]:
            url = testcloud.util.get_centos_image_url(
                matched_centos[0].group(2))
        elif matched_centos[1]:
            url = testcloud.util.get_centos_image_url(
                matched_centos[1].group(2), stream=True)
        elif matched_ubuntu:
            url = testcloud.util.get_ubuntu_image_url(matched_ubuntu.group(2))
        elif matched_debian:
            url = testcloud.util.get_debian_image_url(matched_debian.group(2))
        elif 'rawhide' in name:
            url = testcloud.util.get_fedora_image_url("rawhide")

        if not url:
            raise ProvisionError(f"Could not map '{name}' to compose.")
        return url

    @staticmethod
    def _create_template():
        """ Create libvirt domain template """
        # Write always to ovewrite possible outdated version
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
        self.connection = data.get('connection')

    def save(self):
        """ Save guest data for future wake up """
        data = super().save()
        data['instance'] = self.instance_name
        data['image'] = self.image_url
        data['connection'] = self.connection
        return data

    def wake(self):
        """ Wake up the guest """
        self.debug(
            f"Waking up testcloud instance '{self.instance_name}'.",
            level=2, shift=0)
        self.prepare_config()
        self.image = testcloud.image.Image(self.image_url)
        self.instance = testcloud.instance.Instance(
            self.instance_name, image=self.image,
            connection=f"qemu:///{self.connection}")

    def prepare_ssh_key(self, key_type=None):
        """ Prepare ssh key for authentication """
        # Create ssh key paths
        key_name = "id_{}".format(key_type if key_type is not None else 'rsa')
        self.key = os.path.join(self.workdir, key_name)
        self.pubkey = os.path.join(self.workdir, f'{key_name}.pub')

        # Generate ssh key
        self.debug('Generating an ssh key.')
        command = ["ssh-keygen", "-f", self.key, "-N", ""]
        if key_type is not None:
            command.extend(["-t", key_type])
        self.run(command, shell=False)
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
            self.debug(f"Guessed image url: '{self.image_url}'", level=3)

        # Initialize and prepare testcloud image
        self.image = testcloud.image.Image(self.image_url)
        self.verbose('qcow', self.image.name, 'green')
        if not os.path.exists(self.image.local_path):
            self.info('progress', 'downloading...', 'cyan')
        try:
            self.image.prepare()
        except FileNotFoundError as error:
            raise ProvisionError(
                f"Image '{self.image.local_path}' not found.", original=error)
        except (testcloud.exceptions.TestcloudPermissionsError,
                PermissionError) as error:
            raise ProvisionError(
                f"Failed to prepare the image. Check the '{TESTCLOUD_IMAGES}' "
                f"directory permissions.", original=error)

        # Create instance
        self.instance_name = self._tmt_name()
        self.instance = testcloud.instance.Instance(
            name=self.instance_name, image=self.image,
            connection=f"qemu:///{self.connection}")
        self.verbose('name', self.instance_name, 'green')

        # Decide which networking setup to use
        # Autodetect works with libguestfs python bindings
        # We fall back to basic heuristics based on file name
        # without that installed (eg. from pypi).
        # https://bugzilla.redhat.com/show_bug.cgi?id=1075594
        try:
            import guestfs
        except ImportError:
            match_legacy = re.search(
                r'(rhel|centos).*-7', self.image_url.lower())
            if match_legacy:
                self.instance.pci_net = "e1000"
            else:
                self.instance.pci_net = "virtio-net-pci"

        # Prepare ssh key
        self.prepare_ssh_key(SSH_KEYGEN_TYPE)

        # Boot the virtual machine
        self.info('progress', 'booting...', 'cyan')
        self.instance.ram = self.memory
        self.instance.disk_size = self.disk
        try:
            self.instance.prepare()
            self.instance.spawn_vm()
            self.instance.start(DEFAULT_BOOT_TIMEOUT)
        except (testcloud.exceptions.TestcloudInstanceError,
                libvirt.libvirtError) as error:
            raise ProvisionError(
                f'Failed to boot testcloud instance ({error}).')
        self.guest = self.instance.get_ip()
        self.port = self.instance.get_instance_port()
        self.verbose('ip', self.guest, 'green')
        self.verbose('port', self.port, 'green')
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
        super().stop()
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

    def reboot(self, hard=False):
        """ Reboot the guest, return True if successful """
        if not self.instance:
            raise tmt.utils.ProvisionError("No instance initialized.")
        self.instance.reboot(soft=not hard)
        return self.reconnect()
