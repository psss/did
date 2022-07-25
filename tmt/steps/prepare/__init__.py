import collections
import copy
from typing import Optional, Type

import click
import fmf

import tmt
import tmt.steps
from tmt.steps import Action
from tmt.utils import GeneralError


class Prepare(tmt.steps.Step):
    """
    Prepare the environment for testing.

    Use the 'order' attribute to select in which order preparation
    should happen if there are multiple configs. Default order is '50'.
    Default order of required packages installation is '70', for the
    recommended packages it is '75'.
    """

    def __init__(self, plan, data):
        """ Initialize prepare step data """
        super().__init__(plan=plan, data=data)
        self.preparations_applied = 0

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin = PreparePlugin.delegate(self, data)
            plugin.wake()
            # Add plugin only if there are data
            if len(plugin.data.keys()) > 2:
                self._phases.append(plugin)

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Prepare wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show discover details """
        for data in self.data:
            PreparePlugin.delegate(self, data).show()

    def summary(self):
        """ Give a concise summary of the preparation """
        preparations = fmf.utils.listed(
            self.preparations_applied, 'preparation')
        self.info('summary', f'{preparations} applied', 'green', shift=1)

    def _prepare_roles(self):
        """ Create a mapping of roles to guest names """
        role_mapping = collections.defaultdict(list)
        for guest in self.plan.provision.guests():
            if guest.role:
                role_mapping[guest.role].append(guest.name)
        return role_mapping

    def _prepare_hosts(self):
        """ Create a mapping of guest names to IP addresses """
        host_mapping = {}
        for guest in self.plan.provision.guests():
            if hasattr(guest, 'guest') and guest.guest:
                # FIXME: guest.guest may not be simply an IP address but also
                #        a host name.
                host_mapping[guest.name] = guest.guest
        return host_mapping

    def go(self):
        """ Prepare the guests """
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            self.actions()
            return

        # Required packages
        requires = set(
            self.plan.discover.requires() +
            self.plan.provision.requires() +
            self.plan.prepare.requires() +
            self.plan.execute.requires() +
            self.plan.report.requires() +
            self.plan.finish.requires()
            )

        if requires:
            data = dict(
                how='install',
                name='requires',
                summary='Install required packages',
                order=tmt.utils.DEFAULT_PLUGIN_ORDER_REQUIRES,
                package=list(requires))
            self._phases.append(PreparePlugin.delegate(self, data))

        # Recommended packages
        recommends = self.plan.discover.recommends()
        if recommends:
            data = dict(
                how='install',
                name='recommends',
                summary='Install recommended packages',
                order=tmt.utils.DEFAULT_PLUGIN_ORDER_RECOMMENDS,
                package=recommends,
                missing='skip')
            self._phases.append(PreparePlugin.delegate(self, data))

        # Implicit multihost setup
        if self.plan.provision.is_multihost:
            data = dict(
                how='multihost',
                name='multihost',
                summary='Setup guest for multihost testing',
                order=tmt.utils.DEFAULT_PLUGIN_ORDER_MULTIHOST,
                roles=self._prepare_roles(),
                hosts=self._prepare_hosts(),
                )
            self._phases.append(PreparePlugin.delegate(self, data))

        # Prepare guests (including workdir sync)
        for guest in self.plan.provision.guests():
            guest.push()
            # Create a guest copy and change its parent so that the
            # operations inside prepare plugins on the guest use the
            # prepare step config rather than provision step config.
            guest_copy = copy.copy(guest)
            guest_copy.parent = self
            # Execute each prepare plugin
            for phase in self.phases(classes=(Action, PreparePlugin)):
                if not phase.enabled_on_guest(guest_copy):
                    continue

                if isinstance(phase, Action):
                    phase.go()

                elif isinstance(phase, PreparePlugin):
                    phase.go(guest_copy)

                    self.preparations_applied += 1

                else:
                    raise GeneralError(f'Unexpected phase in prepare step: {phase}')

                self.info('')

            # Pull artifacts created in the plan data directory
            # if there was at least one plugin executed
            if self.phases():
                guest_copy.pull(self.plan.data_directory)

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()

    def requires(self):
        """
        Packages required by all enabled prepare plugins

        Return a list of packages which need to be installed on the
        provisioned guest so that the preparation tasks work well.
        Used by the prepare step.
        """
        requires = set()
        for plugin in self.phases(classes=PreparePlugin):
            requires.update(plugin.requires())
        return list(requires)


class PreparePlugin(tmt.steps.Plugin):
    """ Common parent of prepare plugins """

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    # Common keys for all prepare step implementations
    _common_keys = ['where']

    @classmethod
    def base_command(
            cls,
            usage: str,
            method_class: Optional[Type[click.Command]] = None) -> click.Command:
        """ Create base click command (common for all prepare plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Prepare.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method for environment preparation.')
        def prepare(context, **kwargs):
            context.obj.steps.add('prepare')
            Prepare._save_context(context)

        return prepare

    def go(self, guest):
        """ Prepare the guest (common actions) """
        super().go(guest)

        # Show guest name first in multihost scenarios
        if self.step.plan.provision.is_multihost:
            self.info('guest', guest.name, 'green')

        # Show requested role if defined
        where = self.get('where')
        if where:
            self.info('where', where, 'green')
