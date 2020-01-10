# coding: utf-8

""" Execute Step Class """

import tmt
import os
import shutil

from tmt.steps.execute import shell, beakerlib
from tmt.utils import RUNNER
from fmf.utils import listed
from tmt.utils import GeneralError


class Execute(tmt.steps.Step):
    """ Run tests (using the specified framework and its settings) """
    name = 'execute'
    # supported executors are not loaded automatically, import them and map them in how_map
    how_map = {'shell': shell.ExecutorShell,
               'beakerlib': beakerlib.ExecutorBeakerlib,
               }

    def __init__(self, data, plan):
        """ Initialize the execute step """
        super(Execute, self).__init__(data, plan)
        self.executor = None

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super(Execute, self).wake()
        self._check_data()
        self.executor = self.how_map[self.data['how']](
                self.data, self, name='one')

    def _check_data(self):
        """ Validate input data """
        if len(self.data) > 1:
            raise tmt.utils.SpecificationError("Multiple execute steps defined in '{}'.".format(self.plan))
        self.data = self.data[0]

        # if not specified, use shell as default
        how = self.data.setdefault('how', 'shell')

        # is how supported?
        if how not in self.how_map:
            raise tmt.utils.SpecificationError("How '{}' in plan '{}' is not implemented".format(how, self.plan))

    def show(self):
        """ Show discover details """
        keys = ['how', 'isolate', 'script']
        super(Execute, self).show(keys)

    def go(self):
        """ Execute the test step """
        super(Execute, self).go()

        try:
            self.executor.go(self.plan.workdir)
        except tmt.utils.GeneralError as error:
            self.info('Error occured during test execution.', color='red')
            self.plan.provision.execute('cat nohup.out')

        self.plan.provision.sync_workdir_from_guest()

        output = {}
        for logname in ['stdout.log', 'stderr.log']:
            logpath = os.path.join(self.workdir, logname)
            output[logname] = open(logpath).read()
            self.debug(logname, output[logname], 'yellow')

        # Process the stdout.log
        overview = output['stdout.log'].rstrip('\nD')
        self.verbose('overview', overview, color='green', shift=1)
        passed = 0
        failed = 0
        errors = 0
        for character in output['stdout.log']:
            if character == '.':
                passed += 1
            if character == 'F':
                failed += 1
            if character == 'E':
                errors += 1
        passed = listed(passed, 'test')
        failed = listed(failed, 'test')
        message = f"{passed} passed, {failed} failed"
        self.info('result', message, color='green', shift=1)
        if errors >0:
            raise tmt.utils.GeneralError(f"{errors} errors occured during tests.")

    def sync_runner(self):
        """ Place the runner script to workdir  """
        # Detect location of the runner
        script_path = os.path.join(os.path.dirname(__file__), RUNNER)
        self.debug(f"Copy '{script_path}' to '{self.workdir}'.")
        # Nothing more to do in dry mode
        if self.opt('dry'):
            return
        shutil.copy(script_path, self.workdir)
        # Sync added runner to guests
        self.plan.provision.sync_workdir_to_guest()

    def execute(self, *args, **kwargs):
        """ Execute command on provisioned machine """
        return self.plan.provision.execute(*args, **kwargs)

    # API
    def requires(self):
        """ Returns packages required to run tests - used by prepare step"""
        return self.executor.requires()

    def results(self):
        """ Returns results from executed tests - used by report step """
        return self.executor.results()
