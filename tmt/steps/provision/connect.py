import click

import tmt


class ProvisionConnect(tmt.steps.provision.ProvisionPlugin):
    """
    Connect to a provisioned guest using ssh

    Private key authentication:

        provision:
            how: connect
            guest: host.example.org
            user: root
            key: /home/psss/.ssh/example_rsa

    Password authentication:

        provision:
            how: connect
            guest: host.example.org
            user: root
            password: secret

    User defaults to 'root', so if you have private key correctly set
    the minimal configuration can look like this:

        provision:
            how: connect
            guest: host.example.org
    """

    # Guest instance
    _guest = None

    # Supported methods
    _methods = [tmt.steps.Method(name='connect', doc=__doc__, order=50)]

    # Supported keys
    _keys = ["guest", "key", "user", "password", "port"]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for connect """
        return [
            click.option(
                '-g', '--guest', metavar='GUEST',
                help='Select remote host to connect to (hostname or ip).'),
            click.option(
                '-P', '--port', metavar='PORT',
                help='Use specific port to connect to.'),
            click.option(
                '-k', '--key', metavar='PRIVATE_KEY',
                help='Private key for login into the guest system.'),
            click.option(
                '-u', '--user', metavar='USER',
                help='Username to use for all guest operations.'),
            click.option(
                '-p', '--password', metavar='PASSWORD',
                help='Password for login into the guest system.'),
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        # User root as the default user
        if option == 'user':
            return 'root'
        # No other defaults available
        return default

    def wake(self, keys=None, data=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys, data=data)
        if data:
            self._guest = tmt.Guest(data, name=self.name, parent=self.step)

    def go(self):
        """ Prepare the connection """
        super().go()

        # Check connection details
        guest = self.get('guest')
        user = self.get('user')
        key = self.get('key')
        password = self.get('password')
        port = self.get('port')

        # Check guest and auth info
        if not guest:
            raise tmt.utils.SpecificationError(
                'Provide a host name or an ip address to connect.')
        data = dict(guest=guest, user=user, role=self.get('role'))
        self.info('guest', guest, 'green')
        self.info('user', user, 'green')
        if port:
            self.info('port', port, 'green')
            data['port'] = port

        # Use provided password for authentication
        if password:
            self.info('password', password, 'green')
            self.debug('Using password authentication.')
            data['password'] = password
        # Default to using a private key (user can have configured one)
        else:
            self.info('key', key or 'not provided', 'green')
            self.debug('Using private key authentication.')
            data['key'] = key

        # And finally create the guest
        self._guest = tmt.Guest(data, name=self.name, parent=self.step)

    def guest(self):
        """ Return the provisioned guest """
        return self._guest
