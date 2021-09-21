import tmt


class ProvisionLocal(tmt.steps.provision.ProvisionPlugin):
    """
    Use local host for test execution

    In general it is not recommended to run tests on your local machine
    as there might be security risks. Run only those tests which you
    know are safe so that you don't destroy your laptop ;-)

    Example config:

        provision:
            how: local

    Note that 'tmt run' is expected to be executed under a regular user.
    If there are admin rights required (for example in the prepare step)
    you might be asked for a sudo password.
    """

    # Guest instance
    _guest = None

    # Supported methods
    _methods = [tmt.steps.Method(name='local', doc=__doc__, order=50)]

    def wake(self, keys=None, data=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys, data=data)
        if data:
            self._guest = GuestLocal(data, name=self.name, parent=self.step)

    def go(self):
        """ Provision the container """
        super().go()

        # Create a GuestLocal instance
        data = {'guest': 'localhost', 'role': self.get('role')}
        self._guest = GuestLocal(data, name=self.name, parent=self.step)

    def guest(self):
        """ Return the provisioned guest """
        return self._guest

    def requires(self):
        """ List of required packages needed for workdir sync """
        return GuestLocal.requires()


class GuestLocal(tmt.Guest):
    """ Local Host """

    def ansible(self, playbook, extra_args=None):
        """ Prepare localhost using ansible playbook """
        playbook = self._ansible_playbook_path(playbook)
        stdout, stderr = self.run(
            f'sudo sh -c "stty cols {tmt.utils.OUTPUT_WIDTH}; '
            f'{self._export_environment()}ansible-playbook '
            f'{self._ansible_verbosity()} '
            f'{self._ansible_extra_args(extra_args)} -c local -i localhost,'
            f' {playbook}"')
        self._ansible_summary(stdout)

    def execute(self, command, **kwargs):
        """ Execute command on localhost """
        # Prepare the environment (plan/cli variables override)
        environment = dict()
        environment.update(kwargs.pop('env', dict()))
        environment.update(self.parent.plan.environment)
        # Run the command under the prepared environment
        return self.run(command, env=environment, **kwargs)

    def push(self, source=None, destination=None, options=None):
        """ Nothing to be done to push workdir """

    def pull(self, source=None, destination=None, options=None):
        """ Nothing to be done to pull workdir """

    @classmethod
    def requires(cls):
        """ No packages needed to sync workdir """
        return []
