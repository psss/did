import base64
import click
import datetime
import getpass
import json
import os
import re
import requests
import time
import urllib3.exceptions

import tmt
from tmt.utils import retry_session


DEFAULT_USER = 'root'
SSH_KEY = '/usr/share/qa-tools/1minutetip/1minutetip'
SCRIPT_PATH = '/usr/bin/1minutetip'
NUMBER_OF_RETRIES = 3
DEFAULT_CONNECT_TIMEOUT = 60
NETWORK_NAME_RE = r'provider\_net\_cci'
API_URL_RE = r'PRERESERVE\_URL=\"(?P<url>.+)\"'


def run_openstack(url, cmd, cached_list=False):
    """
    Runs an openstack command.

    Returns (exit_code, stdout) tuple. Both are None if the request failed.
    """
    url += '/openstack.php'
    data = {
        'CMD': base64.b64encode(cmd.encode('ascii')),
        'base64': 1,
        }
    if cached_list:
        data['use_cached_list'] = 1
    # Disable warning about insecure connection. Using insecure connection
    # is unfortunately necessary here for the plugin to work.
    requests.packages.urllib3.disable_warnings(
        category=urllib3.exceptions.InsecureRequestWarning)
    response = retry_session().post(url, verify=False, data=data)
    if response.ok:
        # The output is in the form of: <stdout>\n<exit>\n.
        split = response.text.rsplit('\n', 2)
        return int(split[1]), split[0]
    return None, None


class ProvisionMinute(tmt.steps.provision.ProvisionPlugin):
    """
    Provision guest using 1minutetip backend

    Minimal configuration using the latest Fedora image:

        provision:
            how: minute

    Full configuration example:

        provision:
            how: minute
            image: 1MT-Fedora-32
            flavor: m1.large

    Available images and flavors can be listed using '1minutetip list'
    and '1minutetip list-flavors'.
    """

    # Guest instance
    _guest = None

    # Supported methods
    _methods = [
        tmt.steps.Method(name='minute', doc=__doc__, order=50),
        ]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for 1minutetip """
        return [
            click.option(
                '-i', '--image', metavar='IMAGE',
                help="Image, see '1minutetip list' for options."),
            click.option(
                '-F', '--flavor', metavar='FLAVOR',
                help="Flavor, see '1minutetip list-flavors' for options."),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return the default value for the given option """
        defaults = {
            'image': 'fedora',
            'flavor': 'm1.small'
        }
        return defaults.get(option, default)

    def show(self):
        """ Show provision details """
        super().show(['image', 'flavor'])

    def wake(self, data=None):
        """ Override options and wake up the guest """
        super().wake(['image', 'flavor'])
        if self.opt('dry'):
            return

        # Read API URL from 1minutetip script
        try:
            script_content = self.read(SCRIPT_PATH)
            match = re.search(API_URL_RE, script_content)
            if not match:
                raise tmt.utils.ProvisionError(
                        f"Could not obtain API URL from '{SCRIPT_PATH}'.")
            self.data['api_url'] = match.group('url')
            self.debug('api_url', self.data['api_url'], level=3)
        except tmt.utils.FileError:
            raise tmt.utils.ProvisionError(
                f"File '{SCRIPT_PATH}' not found. Please install 1minutetip.")

        if data:
            self._guest = GuestMinute(data, name=self.name, parent=self.step)
            self._guest.wake()

    def go(self):
        """ Provision the container """
        super().go()

        data = dict(user=DEFAULT_USER)
        for opt in ['image', 'flavor', 'api_url']:
            val = self.get(opt)
            if opt != 'api_url':
                self.info(opt, val, 'green')
            data[opt] = val

        self._guest = GuestMinute(data, name=self.name, parent=self.step)
        self._guest.start()

    def guest(self):
        """ Return the provisioned guest """
        return self._guest


class GuestMinute(tmt.Guest):
    """
    1minutetip instance

    The following keys are expected in the 'data' dictionary:

        image ...... 1minutetip image name
        flavor ..... openstack server flavor to use
        api_url .... URL of 1minutetip's openstack API
    """
    def load(self, data):
        super().load(data)
        self.key = SSH_KEY
        self.api_url = data.get('api_url')
        self.image = data.get('image')
        self.flavor = data.get('flavor')
        self.username = getpass.getuser()
        self.instance_name = data.get('instance')

    def save(self):
        data = super().save()
        data['api_url'] = self.api_url
        data['instance'] = self.instance_name
        data['image'] = self.image
        data['flavor'] = self.flavor
        return data

    def _guess_net_id(self):
        _, networks = run_openstack(
            self.api_url, 'ip availability list -f json')
        networks = json.loads(networks)
        networks = [
            network for network in networks
            if re.match(NETWORK_NAME_RE, network['Network Name'])]
        self.debug(
            f'Available networks:\n{json.dumps(networks, indent=2)}',
            level=2, shift=0)
        if not networks:
            return None, None

        best = max(
            networks, key=lambda x: x.get('Total IPs') - x.get('Used IPs'))
        self.debug(
            f'Using the following network:\n{json.dumps(best, indent=2)}',
            level=2, shift=0)
        return best['Network ID'], best['Network Name']

    def _boot_machine(self):
        """
        Boots a new openstack machine.

        Returns whether the boot was successful (True on success).
        """
        network_id, network_name = self._guess_net_id()
        if not network_id:
            return False

        error, net_info = run_openstack(
            self.api_url,
            f'server create --wait '
            f'--flavor {self.flavor} --image {self.mt_image} '
            f'--nic net-id={network_id} --security-group default '
            f'--property local_user="{self.username}" '
            f'--property reserved_time={self.instance_start} -f value '
            f'-c addresses {self.instance_name}')
        if error is None or error != 0:
            return False

        # Get the IP
        match = re.match(r'\s*{}=(?P<ip>[^ ]+), .*'.format(
            re.escape(network_name)), net_info)
        if not match:
            self.delete()
            return False
        self.guest = match.group('ip')

        # Wait for ssh connection
        for i in range(1, DEFAULT_CONNECT_TIMEOUT):
            try:
                self.execute('whoami')
                break
            except tmt.utils.RunError:
                self.debug('Failed to connect to the machine, retrying.')
            time.sleep(1)

        if i == DEFAULT_CONNECT_TIMEOUT:
            self.delete()
            return False
        return True

    def _setup_machine(self):
        response = retry_session().get(
            f'{self.api_url}?image_name={self.mt_image}'
            f'&user={self.username}&osver=rhos10', verify=False)
        if not response.ok:
            return
        # No prereserved machine, boot a new one
        if 'prereserve' not in response.text:
            return self._boot_machine()
        # Rename the prereserved machine
        old_name, self.guest = response.text.split()
        _, rename_out = run_openstack(
            self.api_url, f'server set --name {self.instance_name} {old_name}')
        if rename_out is None or 'ERROR' in rename_out:
            return False
        # Machine renamed, set properties
        run_openstack(
            self.api_url,
            f'server set --property local_user={self.username} '
            f'--property reserved_time={self.instance_start}')
        return True

    def _convert_image(self, image):
        """
        Convert the given image to 1MT image name

        Raises a ProvisionError if the given image name is not valid.
        The given image can be shortened, the supported formats are:

        Fedora images:
            fedora (latest fedora)
            fedoraX
            fedora-X
            fcX
            fc-X
            fX
            f-X

        RHEL images:
            rhelX
            rhel-X

        CentOS images:
            centosX
            centos-X
        """
        mt_image = image
        image_lower = image.lower().strip()
        _, images = run_openstack(
            self.api_url, 'image list -f value -c Name', True)
        images = images.splitlines()

        # Use the latest Fedora image
        if image_lower == 'fedora':
            fedora_re = re.compile(r'1MT-Fedora-(?P<ver>\d+)')
            fedora_images = [
                image for image in images if fedora_re.match(image)]
            mt_image = sorted(fedora_images)[-1]

        # Fedora shortened names
        fedora_match = re.match(r'^f(c|edora)?-?(?P<ver>\d+)$', image_lower)
        if fedora_match:
            mt_image = f'1MT-Fedora-{fedora_match.group("ver")}'

        # RHEL shortened names
        rhel_match = re.match(r'^rhel-?(?P<ver>\d+)$', image_lower)
        if rhel_match:
            rhel_re = re.compile(r'1MT-RHEL-*{}'.format(
                re.escape(rhel_match.group('ver'))))
            # Remove obsolete and invalid images
            invalid_re = re.compile(r'(new|obsolete|invalid|fips)$')
            rhel_images = [
                image for image in images
                if rhel_re.match(image) and not invalid_re.search(image)]

            # Use the last image (newest RHEL)
            mt_image = rhel_images[-1]

        # CentOS shortened names
        centos_match = re.match(r'^centos-?(?P<ver>\d+)$', image_lower)
        if centos_match:
            mt_image = f'1MT-CentOS-{centos_match.group("ver")}'

        # Check if the image is valid
        if not mt_image in images:
            raise tmt.utils.ProvisionError(
                f"Image '{image}' is not a valid 1minutetip image.")
        return mt_image

    def start(self):
        """ Start provisioned guest """
        if self.opt('dry'):
            return
        self.mt_image = self._convert_image(self.image)
        self.instance_start = datetime.datetime.utcnow().strftime(
            '%Y-%m-%d-%H-%M')
        self.instance_name = (
            f'{self.username}-{self.mt_image}-'
            f'{os.getpid()}-{self.instance_start}')
        for i in range(NUMBER_OF_RETRIES):
            if self._setup_machine():
                return

        raise tmt.utils.ProvisionError(
            "All attempts to provision a machine with 1minutetip failed.")

    def delete(self):
        run_openstack(self.api_url, f'server delete {self.instance_name}')

    def remove(self):
        """ Remove the guest """
        if self.instance_name:
            self.info('guest', 'removed', 'green')
            self.delete()
            self.instance_name = None
