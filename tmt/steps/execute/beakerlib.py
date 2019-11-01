from tmt.steps.execute.shell import ExecutorShell

""" Beakerlib Executor Provider Class """


class ExecutorBeakerlib(ExecutorShell):
    """ Run tests using how: beakerlib """
    type = 'beakerlib'

    def __init__(self,  data, step=None, name=None):
        super(ExecutorBeakerlib, self).__init__(data, step, name)

    def go(self, plan_workdir):
        """ Run tests """
        super(ExecutorBeakerlib, self).go(plan_workdir)

    # API
    def requires(self):
        """ Returns packages required to run tests"""
        super(ExecutorBeakerlib, self).requires()
        packages = (
            'beakerlib',
        )
        return packages

    def results(self):
        """ Returns results from executed tests """
        super(ExecutorBeakerlib, self).results()
