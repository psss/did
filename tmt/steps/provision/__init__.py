import os
import click

import fmf
import tmt

class Provision(tmt.steps.Step):
    """ Provision an environment for testing or use localhost """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    def __init__(self, data, plan):
        """ Initialize provision step data """
        super().__init__(data, plan)
        # List of provisioned guests and loaded guest data
        self._guests = []
        self._guest_data = {}

    def load(self):
        """ Load guest data from the workdir """
        super().load()
        try:
            self._guest_data = tmt.utils.yaml_to_dict(self.read('guests.yaml'))
        except tmt.utils.FileError:
            self.debug('Provisioned guests not found.', level=2)

    def save(self):
        """ Save guest data to the workdir """
        super().save()
        try:
            guests = dict(
                [(guest.name, guest.save()) for guest in self.guests()])
            self.write('guests.yaml', tmt.utils.dict_to_yaml(guests))
        except tmt.utils.FileError:
            self.debug('Failed to save provisioned guests.')

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin = ProvisionPlugin.delegate(self, data)
            self._plugins.append(plugin)
            # If guest data loaded, perform a complete wake up
            plugin.wake(data=self._guest_data.get(plugin.name))
            if plugin.guest():
                self._guests.append(plugin.guest())

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Provision wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show discover details """
        for data in self.data:
            ProvisionPlugin.delegate(self, data).show()

    def summary(self):
        """ Give a concise summary of the provisioning """
        # Summary of provisioned guests
        guests = fmf.utils.listed(self.guests(), 'guest')
        self.info('summary', f'{guests} provisioned', 'green', shift=1)
        # Guest list in verbose mode
        for guest in self.guests():
            if guest.name != tmt.utils.DEFAULT_NAME:
                self.verbose(guest.name, color='red', shift=2)

    def go(self):
        """ Provision all guests"""
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            return

        # Provision guests
        self._guests = []
        for plugin in self.plugins():
            plugin.go()
            if isinstance(plugin, ProvisionPlugin):
                plugin.guest().details()
                self._guests.append(plugin.guest())

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()

    def guests(self):
        """ Return the list of all provisioned guests """
        return self._guests


class ProvisionPlugin(tmt.steps.Plugin):
    """ Common parent of provision plugins """

    # Default implementation for provision is a virtual machine
    how = 'virtual'

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    @classmethod
    def base_command(cls, method_class=None, usage=None):
        """ Create base click command (common for all provision plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Provision.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method for provisioning.')
        def provision(context, **kwargs):
            context.obj.steps.add('provision')
            Provision._save_context(context)

        return provision

    def wake(self, options=None, data=None):
        """
        Wake up the plugin

        Override data with command line options.
        Wake up the guest based on provided guest data.
        """
        super().wake(options)

    def guest(self):
        """
        Return provisioned guest

        Each ProvisionPlugin has to implement this method.
        Should return a provisioned Guest() instance.
        """
        raise NotImplementedError
