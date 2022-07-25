import os
from typing import TYPE_CHECKING, Any, List, Optional, Type

import click
from fmf.utils import listed

import tmt

if TYPE_CHECKING:
    import tmt.steps
    import tmt.options

import tmt.steps
import tmt.utils
from tmt.steps import Action
from tmt.utils import GeneralError


class Discover(tmt.steps.Step):
    """ Gather information about test cases to be executed. """

    data: List[tmt.steps.StepData]

    def __init__(self, plan: 'tmt.base.Plan', data: tmt.steps.StepData):
        """ Store supported attributes, check for sanity """
        super().__init__(plan=plan, data=data)

        # List of Test() objects representing discovered tests
        self._tests: List[tmt.Test] = []

    def load(self, extra_keys: Optional[List[str]] = None) -> None:
        """ Load step data from the workdir """
        extra_keys = extra_keys or []
        super().load(extra_keys)
        try:
            tests = tmt.utils.yaml_to_dict(self.read('tests.yaml'))
            self._tests = [
                tmt.Test(data, name) for name, data in tests.items()]
        except tmt.utils.FileError:
            self.debug('Discovered tests not found.', level=2)

    def save(self, data: Optional[tmt.steps.StepData] = None) -> None:
        """ Save step data to the workdir """
        data = data or {}
        super().save(data)

        # Create tests.yaml with the full test data
        tests = dict([
            (test.name, test.export(format_='dict'))
            for test in self.tests()])
        self.write('tests.yaml', tmt.utils.dict_to_yaml(tests))

        # Create 'run.yaml' with the list of tests for the executor
        if not self.tests():
            return
        tests = dict([
            (test.name, test.export(format_='execute'))
            for test in self.tests()])
        self.write('run.yaml', tmt.utils.dict_to_yaml(tests, width=1000000))

    def _discover_from_execute(self) -> None:
        """ Check the execute step for possible shell script tests """

        # Check scripts for command line and data, convert to list if needed
        scripts = self.plan.execute.opt('script')
        if not scripts:
            scripts = self.plan.execute.data[0].get('script')
        if not scripts:
            return
        if isinstance(scripts, str):
            scripts = [scripts]

        # Give a warning when discover step defined as well
        default_data = [{'name': 'default', 'how': 'shell'}]
        if self.data and self.data != default_data:
            raise tmt.utils.DiscoverError(
                "Use either 'discover' or 'execute' step "
                "to define tests, but not both.")

        # Check the execute step for possible custom duration limit
        duration = self.plan.execute.data[0].get(
            'duration', tmt.base.DEFAULT_TEST_DURATION_L2)

        # Prepare the list of tests
        tests = []
        for index, script in enumerate(scripts):
            name = f'script-{str(index).zfill(2)}'
            tests.append(dict(name=name, test=script, duration=duration))

        # Append new data if tests already defined
        if self.data[0].get('tests'):
            self.data.append(
                dict(how='shell', tests=tests, name='execute'))
        # Otherwise override current empty definition
        else:
            self.data[0]['tests'] = tests

    def wake(self) -> None:
        """ Wake up the step (process workdir and command line) """
        super().wake()

        # Check execute step for possible tests (unless already done)
        if self.status() is None:
            self._discover_from_execute()

        # Choose the right plugin and wake it up
        for data in self.data:
            plugin = DiscoverPlugin.delegate(self, data)
            self._phases.append(plugin)
            plugin.wake()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.debug(
                'Discover wake up complete (already done before).', level=2)
        # Save status and step data (now we know what to do)
        else:
            self.status('todo')
            self.save()

    def show(self) -> None:
        """ Show discover details """
        for data in self.data:
            DiscoverPlugin.delegate(self, data).show()

    def summary(self) -> None:
        """ Give a concise summary of the discovery """
        # Summary of selected tests
        text = listed(len(self.tests()), 'test') + ' selected'
        self.info('summary', text, 'green', shift=1)
        # Test list in verbose mode
        for test in self.tests():
            self.verbose(test.name, color='red', shift=2)

    def go(self) -> None:
        """ Execute all steps """
        super().go()

        # Nothing more to do if already done
        if self.status() == 'done':
            self.info('status', 'done', 'green', shift=1)
            self.summary()
            self.actions()
            return

        # Perform test discovery, gather discovered tests
        self._tests = []
        for phase in self.phases(classes=(Action, DiscoverPlugin)):
            if isinstance(phase, Action):
                phase.go()

            elif isinstance(phase, DiscoverPlugin):
                # Go and discover tests
                phase.go()

                # Prefix test name only if multiple plugins configured
                prefix = f'/{phase.name}' if len(self.phases()) > 1 else ''
                # Check discovered tests, modify test name/path
                for test in phase.tests():
                    test.name = f"{prefix}{test.name}"
                    test.path = f"/{phase.name}{test.path}"
                    # Use the default test framework if not defined in L1
                    # FIXME remove when we drop the old execution methods
                    if not test.framework:
                        test.framework = self.plan.execute._framework
                    # Update test environment with plan environment
                    test.environment.update(self.plan.environment)
                    self._tests.append(test)

            else:
                raise GeneralError(f'Unexpected phase in discover step: {phase}')

        # Show fmf identifiers for tests discovered in plan
        # TODO: This part should go into the 'fmf.py' module
        if self.opt('fmf_id'):
            if self.tests():
                fmf_id_list = [tmt.utils.dict_to_yaml(test.fmf_id, start=True)
                               for test in self.tests()
                               if 'url' in test.fmf_id]
                click.echo(''.join(fmf_id_list), nl=False)
            return

        # Give a summary, update status and save
        self.summary()
        self.status('done')
        self.save()

    def tests(self) -> List['tmt.Test']:
        """ Return the list of all enabled tests """
        return [test for test in self._tests if test.enabled]

    def requires(self) -> List[str]:
        """ Return all tests' requires """
        requires = set()
        for test in self.tests():
            for value in getattr(test, 'require', []):
                requires.add(value)
        return list(requires)

    def recommends(self) -> List[str]:
        """ Return all packages recommended by tests """
        recommends = set()
        for test in self.tests():
            for value in getattr(test, 'recommend', []):
                recommends.add(value)
        return list(recommends)


class DiscoverPlugin(tmt.steps.GuestlessPlugin):
    """ Common parent of discover plugins """

    # List of all supported methods aggregated from all plugins
    _supported_methods: List[tmt.steps.Method] = []

    # Common keys for all discover step implementations
    _common_keys = [
        "dist-git-source",
        "dist-git-type",
        ]

    @classmethod
    def base_command(
            cls,
            usage: str,
            method_class: Optional[Type[click.Command]] = None) -> click.Command:
        """ Create base click command (common for all discover plugins) """

        # Prepare general usage message for the step
        if method_class:
            usage = Discover.usage(method_overview=usage)

        # Create the command
        @click.command(cls=method_class, help=usage)
        @click.pass_context
        @click.option(
            '-h', '--how', metavar='METHOD',
            help='Use specified method to discover tests.')
        def discover(context: click.Context, **kwargs: Any) -> None:
            # TODO: This part should go into the 'fmf.py' module
            if kwargs.get('fmf_id'):
                # Set quiet, disable debug and verbose to avoid logging
                # to terminal with discover --fmf-id
                assert context.parent is not None
                context.parent.params['quiet'] = True
                context.parent.params['debug'] = 0
                context.parent.params['verbose'] = 0
            context.obj.steps.add('discover')
            Discover._save_context(context)

        return discover

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options for given method """
        options = super().options(how)
        options[:0] = [
            click.option(
                '--dist-git-source',
                is_flag=True,
                help='Extract DistGit sources.'),
            click.option(
                '--dist-git-type',
                type=click.Choice(tmt.utils.get_distgit_handler_names()),
                help='Use the provided DistGit handler '
                     'instead of the auto detection.'),
            ]
        return options

    def tests(self) -> List['tmt.Test']:
        """
        Return discovered tests

        Each DiscoverPlugin has to implement this method.
        Should return a list of Test() objects.
        """
        raise NotImplementedError

    def extract_distgit_source(
            self, distgit_dir: str, target_dir: str, handler_name: Optional[str] = None) -> None:
        """
        Extract source tarball into target_dir

        distgit_dir is path to the DistGit repository.
        Source tarball is discovered from the 'sources' file content.
        """
        if handler_name is None:
            stdout, _ = self.run(
                ["git", "config", "--get-regexp", '^remote\\..*.url'],
                cwd=distgit_dir)
            if stdout is None:
                raise tmt.utils.GeneralError("Missing remote origin url.")

            remotes = stdout.split('\n')
            handler = tmt.utils.get_distgit_handler(remotes=remotes)
        else:
            handler = tmt.utils.get_distgit_handler(usage_name=handler_name)
        for url, source_name in handler.url_and_name(distgit_dir):
            if handler.re_ignore_extensions.search(source_name):
                continue
            self.debug(f"Download sources from '{url}'.")
            with tmt.utils.retry_session() as session:
                response = session.get(url)
            response.raise_for_status()
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, source_name), 'wb') as tarball:
                tarball.write(response.content)
            self.run(
                ["tar", "--auto-compress", "--extract", "-f", source_name],
                cwd=target_dir)
