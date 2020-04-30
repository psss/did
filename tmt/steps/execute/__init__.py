import re
import fmf
import tmt
import click


class Execute(tmt.steps.Step):
    """ Run tests using the specified framework """

    def __init__(self, data, plan):
        """ Initialize execute step data """
        super().__init__(data, plan)
        self.executor = None
        # List of Result() objects representing test results
        self._results = []

    def load(self):
        """ Load test results """
        super().load()
        try:
            results = tmt.utils.yaml_to_dict(self.read('results.yaml'))
            self._results = [
                tmt.Result(data, test) for test, data in results.items()]
        except tmt.utils.FileError as error:
            self.debug('Test results not found.', level=2)

    def save(self):
        """ Save test results to the workdir """
        super().save()
        results = dict([
            (result.name, result.export()) for result in self.results()])
        self.write('results.yaml', tmt.utils.dict_to_yaml(results))

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # There should be just a single definition
        if len(self.data) > 1:
            raise tmt.utils.SpecificationError(
                "Multiple execute steps defined in '{}'.".format(self.plan))

        # Choose the right plugin and wake it up
        self.executor = ExecutePlugin.delegate(self, self.data[0])
        self.executor.wake()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Execute wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self):
        """ Show execute details """
        ExecutePlugin.delegate(self, self.data[0]).show()

    def summary(self):
        """ Give a concise summary of the execution """
        tests = fmf.utils.listed(self.results(), 'test')
        self.info('summary', f'{tests} executed', 'green', shift=1)

    def go(self):
        """ Execute tests """
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            return

        # Make sure that guests are prepared
        if not self.plan.provision.guests():
            raise tmt.utils.ExecuteError("No guests available for execution.")

        # Execute the tests, store results
        self.executor.go()
        self._results = self.executor.results()

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()

    def requires(self):
        """
        Packages required for test execution

        Return a list of packages which need to be installed on the
        guest so that tests can be executed. Used by the prepare step.
        """
        return self.executor.requires()

    def results(self):
        """
        Results from executed tests

        Return a dictionary with test results according to the spec:
        https://tmt.readthedocs.io/en/latest/spec/steps.html#execute
        """
        return self._results


class ExecutePlugin(tmt.steps.Plugin):
    """ Common parent of execute plugins """

    # List of all supported methods aggregated from all plugins
    _supported_methods = []

    @classmethod
    def base_command(cls, method_class=None, usage=None):
        """ Create base click command (common for all execute plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Execute.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method for test execution.')
        def execute(context, **kwargs):
            context.obj.steps.add('execute')
            Execute._save_context(context)

        return execute
