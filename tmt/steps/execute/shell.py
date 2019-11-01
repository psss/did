from tmt.steps.execute.base import ExecutorBase

""" Shell Executor Provider Class """


class ExecutorShell(ExecutorBase):
    """ Run tests using how: shell """
    type = 'shell'

    def __init__(self,  data, step=None, name=None):
        super(ExecutorShell, self).__init__(data, step, name)

    def go(self, plan_workdir):
        """ Run tests """
        super(ExecutorShell, self).go(plan_workdir)
        # we need run.sh synced to workdir
        self.step.sync_run_sh()
        cmd = f'{self.step.workdir}/run.sh -v {plan_workdir} {self.type}'
        self.step.run(cmd)

    # API
    def requires(self):
        """ Returns packages required to run tests"""
        super(ExecutorShell, self).requires()
        return ()

    def results(self):
        """ Returns results from executed tests """
        super(ExecutorShell, self).results()
