# coding: utf-8

""" Shell Executor Provider Class """

from tmt.steps.execute.base import ExecutorBase
from tmt.utils import RUNNER


class ExecutorShell(ExecutorBase):
    """ Run tests using how: shell """
    type = 'shell'

    def go(self, plan_workdir):
        """ Run tests """
        super(ExecutorShell, self).go(plan_workdir)
        # we need run.sh synced to workdir
        self.step.sync_runner()

        self.step.execute('nohup',
            f'{self.step.workdir}/{RUNNER}',
            '-v',
            plan_workdir,
            self.type,
            f'{self.step.workdir}/stdout.log',
            f'{self.step.workdir}/stderr.log')

    # API
    def requires(self):
        """ Returns packages required to run tests"""
        super(ExecutorShell, self).requires()
        return ()

    def results(self):
        """ Returns results from executed tests """
        super(ExecutorShell, self).results()
