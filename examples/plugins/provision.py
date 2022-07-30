import click

import tmt
import tmt.steps

# See the online documentation for more details about writing plugins
# https://tmt.readthedocs.io/en/stable/plugins.html


@tmt.steps.provides_method('example')
class ProvisionExample(tmt.steps.provision.ProvisionPlugin):
    """
    Provision guest using nothing. Just example

    Minimal configuration using the latest nothing image:

        provision:
            how: example

    Full configuration example:

        provision:
            how: example
    """

    _guest = None

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for example """
        return [
            click.option(
                '-w', '--what', metavar='WHAT',
                help="Example how to pass value."),
            click.option(
                '-s', '--switch', is_flag=True,
                help="Example how to enable something.")
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return the default value for the given option """
        defaults = {
            'what': 'default value',
            'switch': False,
            }
        return defaults.get(option, default)

    def show(self):
        """ Show provision details """
        super().show(['what', 'switch'])

    def wake(self, data=None):
        """
        Wake up the plugin

        Override data with command line options.
        Wake up the guest based on provided guest data.
        """
        super().wake(['what', 'switch'])
        print("wake() called")

        # Don't schedule anything if ve are in dry mode
        if self.opt('dry'):
            return

        if data:
            self._guest = GuestExample(data, name=self.name, parent=self.step)
            self._guest.wake()

    def go(self):
        """ Provision the container """
        super().go()
        print("go() called")

        # Data dictionary is used to pass information among classes.
        data = dict(what='Another default what. Object variable can be used.')

        for opt in ['what', 'switch']:
            val = self.get(opt)
            # You can hide some not important information about provisioning.
            if opt != 'switch':
                self.info(opt, val, 'green')
            data[opt] = val

        self._guest = GuestExample(data, name=self.name, parent=self.step)
        self._guest.start()

    def guest(self):
        """
        Return provisioned guest

        Each ProvisionPlugin has to implement this method.
        Should return a provisioned Guest() instance.
        """
        return self._guest


class GuestExample(tmt.Guest):
    """
    Guest provisioned for test execution

    The following keys are expected in the 'data' dictionary::

    guest ...... hostname or ip address
    port ....... port to connect to
    user ....... user name to log in
    key ........ private key
    password ... password

    These are by default imported into instance attributes (see the
    class attribute '_keys' in tmt.Guest class).

    Example instance:

    The following keys are expected in the 'data' dictionary:

        what ...... content of cli what
        switch .... flag passed via cli
    """

    def load(self, data):
        """
        Load guest data into object attributes for easy access

        Called during guest object initialization. Takes care of storing
        all supported keys (see class attribute _keys in tmt.Guest class
        for the list) from provided data to the guest object attributes.
        Child classes can extend it to make additional guest attributes
        easily available.

        Data dictionary can contain guest information from both command
        line options / L2 metadata / user configuration and wake up data
        stored by the save() method below.
        """
        super().load(data)
        self.what = data.get('what')
        self.switch = data.get('switch')

    def wake(self):
        """
        Wake up the guest

        Perform any actions necessary after step wake up to be able to
        attach to a running guest instance and execute commands. Called
        after load() is completed so all guest data should be prepared.
        """
        print("wake() called")

    def save(self):
        """
        Save guest data for future wake up

        Export all essential guest data into a dictionary which will be
        stored in the `guests.yaml` file for possible future wake up of
        the guest. Everything needed to attach to a running instance
        should be added into the data dictionary by child classes.
        """
        data = super().save()
        data['what'] = self.what
        data['switch'] = self.switch
        return data

    def _some_your_internal_stuff(self):
        """ Do some heavy lifting """
        return True

    def start(self):
        """
        Start the guest

        Get a new guest instance running. This should include preparing
        any configuration necessary to get it started. Called after
        load() is completed so all guest data should be available.
        """

        print("start() called")

        if self.opt('dry'):
            return

        self.verbose('what', self.what, 'green')

        if self._some_your_internal_stuff():
            return

        raise tmt.utils.ProvisionError(
            "All attempts to provision a machine with example failed.")

    # For advanced development
    def execute(self, command, **kwargs):
        """
        Optionally you can overload how commands going to be executed
        on guest (provisioned machine). If you don't want to use
        ssh to connect to guest, you need to overload this method
        however you need to provide some expected information.

        Execute command on the guest

            command ... string or list of command arguments (required)
            env ....... dictionary with environment variables
            cwd ....... working directory to be entered before execution

        If the command is provided as a list, it will be space-joined.
        If necessary, quote escaping has to be handled by the caller.
        """

        print("execute() called. This is an optional overload...")

        output = ["Fedora", "whatever"]
        return output

    def delete(self):
        """ Remove the example instance """
        self.debug("You should place code for cleanup here.")

    def remove(self):
        """ Remove the guest """
        if self.what:
            self.info('guest', 'removed', 'green')
            self.delete()
            self.what = None
