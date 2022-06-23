# coding: utf-8

""" Command line interface for the Test Management Tool """

import dataclasses
import os
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Set

import click
import fmf
from click import echo, style
from fmf.utils import listed

import tmt
import tmt.convert
import tmt.export
import tmt.identifier
import tmt.options
import tmt.plugins
import tmt.steps
import tmt.templates
import tmt.utils

if TYPE_CHECKING:
    import tmt.steps.discover
    import tmt.steps.execute

# Explore available plugins (need to detect all supported methods first)
tmt.plugins.explore()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Click Context Object Container
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@dataclasses.dataclass
class ContextObject:
    """ Click Context Object Container """
    common: tmt.utils.Common
    fmf_context: tmt.utils.FmfContextType
    steps: Set[tmt.steps.Step]
    tree: tmt.Tree
    clean: Optional[tmt.Clean] = None
    run: Optional[tmt.Run] = None


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Custom Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CustomGroup(click.Group):
    """ Custom Click Group """

    def list_commands(self, context: click.core.Context) -> List[str]:
        """ Prevent alphabetical sorting """
        return list(self.commands.keys())

    def get_command(self, context: click.core.Context, cmd_name: str) -> Optional[click.Command]:
        """ Allow command shortening """
        # Backward-compatible 'test convert' (just temporary for now FIXME)
        cmd_name = cmd_name.replace('convert', 'import')
        # Support both story & stories
        cmd_name = cmd_name.replace('story', 'stories')
        found = click.Group.get_command(self, context, cmd_name)
        if found is not None:
            return found
        matches = [command for command in self.list_commands(context)
                   if command.startswith(cmd_name)]
        if not matches:
            return None
        elif len(matches) == 1:
            return click.Group.get_command(self, context, matches[0])
        context.fail('Did you mean {}?'.format(
            listed(sorted(matches), join='or')))
        return None


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Common Options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def verbose_debug_quiet(function: Callable[..., Any]) -> Callable[..., Any]:
    """ Verbose, debug and quiet output """
    for option in reversed(tmt.options.verbose_debug_quiet):
        function = option(function)
    return function


def force_dry(function: Callable[..., Any]) -> Callable[..., Any]:
    """ Force and dry actions """
    for option in reversed(tmt.options.force_dry):
        function = option(function)
    return function


def fix(function: Callable[..., Any]) -> Callable[..., Any]:
    """ Fix action """
    function = tmt.options.fix(function)
    return function


def name_filter_condition(function: Callable[..., Any]) -> Callable[..., Any]:
    """ Common filter options (short & long) """
    options = [
        click.argument(
            'names', nargs=-1, metavar='[REGEXP|.]'),
        click.option(
            '-f', '--filter', 'filters', metavar='FILTER', multiple=True,
            help="Apply advanced filter (see 'pydoc fmf.filter')."),
        click.option(
            '-c', '--condition', 'conditions', metavar="EXPR", multiple=True,
            help="Use arbitrary Python expression for filtering."),
        click.option(
            '--link', 'links', metavar="RELATION:TARGET", multiple=True,
            help="Filter by linked objects (regular expressions are "
                 "supported for both relation and target)."),
        click.option(
            '-x', '--exclude', 'exclude', metavar='[REGEXP]', multiple=True,
            help="Exclude a regular expression from search result."),
        ]

    for option in reversed(options):
        function = option(function)
    return function


def source(function: Callable[..., Any]) -> Callable[..., Any]:
    """ Option to select fmf objects by their sources """
    return click.option(
        '--source', is_flag=True, help="Select by fmf source file names instead of object names."
        )(function)


def name_filter_condition_long(function: Callable[..., Any]) -> Callable[..., Any]:
    """ Common filter options (long only) """
    options = [
        click.argument(
            'names', nargs=-1, metavar='[REGEXP|.]'),
        click.option(
            '--filter', 'filters', metavar='FILTER', multiple=True,
            help="Apply advanced filter (see 'pydoc fmf.filter')."),
        click.option(
            '--condition', 'conditions', metavar="EXPR", multiple=True,
            help="Use arbitrary Python expression for filtering."),
        click.option(
            '--link', 'links', metavar="RELATION:TARGET", multiple=True,
            help="Filter by linked objects (regular expressions are "
                 "supported for both relation and target)."),
        click.option(
            '--exclude', 'exclude', metavar='[REGEXP]', multiple=True,
            help="Exclude a regular expression from search result."),
        ]

    for option in reversed(options):
        function = option(function)
    return function


def implemented_verified_documented(function: Callable[..., Any]) -> Callable[..., Any]:
    """ Common story options """

    options = [
        click.option(
            '--implemented', is_flag=True,
            help='Implemented stories only.'),
        click.option(
            '--unimplemented', is_flag=True,
            help='Unimplemented stories only.'),
        click.option(
            '--verified', is_flag=True,
            help='Stories verified by tests.'),
        click.option(
            '--unverified', is_flag=True,
            help='Stories not verified by tests.'),
        click.option(
            '--documented', is_flag=True,
            help='Documented stories only.'),
        click.option(
            '--undocumented', is_flag=True,
            help='Undocumented stories only.'),
        click.option(
            '--covered', is_flag=True,
            help='Covered stories only.'),
        click.option(
            '--uncovered', is_flag=True,
            help='Uncovered stories only.'),
        ]

    for option in reversed(options):
        function = option(function)
    return function


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Main
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@click.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@click.option(
    '-r', '--root', metavar='PATH', show_default=True,
    help="Path to the tree root, '.' by default.")
@click.option(
    '-c', '--context', metavar='DATA', multiple=True,
    help='Set the fmf context. Use KEY=VAL or KEY=VAL1,VAL2... format '
         'to define individual dimensions or the @FILE notation to load data '
         'from provided yaml file. Can be specified multiple times. ')
@verbose_debug_quiet
@click.option(
    '--version', is_flag=True,
    help='Show tmt version and commit hash.')
def main(
        click_contex: click.core.Context,
        root: str,
        context: List[str],
        **kwargs: Any) -> None:
    """ Test Management Tool """
    # Show current tmt version and exit
    if kwargs.get('version'):
        print(f"tmt version: {tmt.__version__}")
        raise SystemExit(0)

    # Disable coloring if NO_COLOR is set
    if 'NO_COLOR' in os.environ:
        click_contex.color = False

    # Save click context and fmf context for future use
    tmt.utils.Common._save_context(click_contex)

    # Initialize metadata tree (from given path or current directory)
    tree = tmt.Tree(root or os.curdir)

    # TODO: context object details need checks
    click_contex.obj = ContextObject(
        common=tmt.utils.Common(),
        fmf_context=tmt.utils.context_to_dict(context),
        steps=set(),
        tree=tree
        )

    # Show overview of available tests, plans and stories
    if click_contex.invoked_subcommand is None:
        tmt.Test.overview(tree)
        tmt.Plan.overview(tree)
        tmt.Story.overview(tree)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Run
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(chain=True, invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@click.option(
    '-i', '--id', 'id_', help='Run id (name or directory path).', metavar="ID")
@click.option(
    '-l', '--last', help='Execute the last run once again.', is_flag=True)
@click.option(
    '-r', '--rm', '--remove', 'remove', is_flag=True,
    help='Remove the workdir when test run is finished.')
@click.option(
    '--scratch', is_flag=True,
    help='Remove the run workdir before executing to start from scratch.')
@click.option(
    '--follow', is_flag=True,
    help='Output the logfile as it grows.')
@click.option(
    '-a', '--all', help='Run all steps, customize some.', is_flag=True)
@click.option(
    '-u', '--until', type=click.Choice(tmt.steps.STEPS), metavar='STEP',
    help='Enable given step and all preceding steps.')
@click.option(
    '-s', '--since', type=click.Choice(tmt.steps.STEPS), metavar='STEP',
    help='Enable given step and all following steps.')
@click.option(
    '-A', '--after', type=click.Choice(tmt.steps.STEPS), metavar='STEP',
    help='Enable all steps after the given one.')
@click.option(
    '-B', '--before', type=click.Choice(tmt.steps.STEPS), metavar='STEP',
    help='Enable all steps before the given one.')
@click.option(
    '-S', '--skip', type=click.Choice(tmt.steps.STEPS), metavar='STEP',
    help='Skip given step(s) during test run execution.', multiple=True)
@click.option(
    '-e', '--environment', metavar='KEY=VALUE|@FILE', multiple=True,
    help='Set environment variable. Can be specified multiple times. The '
         '"@" prefix marks a file to load (yaml or dotenv formats supported).')
@click.option(
    '--environment-file', metavar='FILE|URL', multiple=True,
    help='Set environment variables from file or url (yaml or dotenv formats '
         'are supported). Can be specified multiple times.')
@verbose_debug_quiet
@force_dry
def run(context: click.core.Context, id_: str, **kwargs: Any) -> None:
    """ Run test steps. """
    # Initialize
    run = tmt.Run(id_, context.obj.tree, context=context)
    context.obj.run = run


# Steps options
run.add_command(tmt.steps.discover.DiscoverPlugin.command())
run.add_command(tmt.steps.provision.ProvisionPlugin.command())
run.add_command(tmt.steps.prepare.PreparePlugin.command())
run.add_command(tmt.steps.execute.ExecutePlugin.command())
run.add_command(tmt.steps.report.ReportPlugin.command())
run.add_command(tmt.steps.finish.FinishPlugin.command())
run.add_command(tmt.steps.Login.command())
run.add_command(tmt.steps.Reboot.command())


@run.command(name='plans')
@click.pass_context
@click.option(
    '-n', '--name', 'names', metavar='[REGEXP|.]', multiple=True,
    help="Regular expression to match plan name or '.' for current directory.")
@click.option(
    '-f', '--filter', 'filters', metavar='FILTER', multiple=True,
    help="Apply advanced filter (see 'pydoc fmf.filter').")
@click.option(
    '-c', '--condition', 'conditions', metavar="EXPR", multiple=True,
    help="Use arbitrary Python expression for filtering.")
@click.option(
    '--link', 'links', metavar="RELATION:TARGET", multiple=True,
    help="Filter by linked objects (regular expressions are "
         "supported for both relation and target).")
@click.option(
    '--default', is_flag=True,
    help="Use default plans even if others are available.")
@verbose_debug_quiet
def run_plans(context: click.core.Context, **kwargs: Any) -> None:
    """
    Select plans which should be executed.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.base.Plan._save_context(context)


@run.command(name='tests')
@click.pass_context
@click.option(
    '-n', '--name', 'names', metavar='[REGEXP|.]', multiple=True,
    help="Regular expression to match test name or '.' for current directory.")
@click.option(
    '-f', '--filter', 'filters', metavar='FILTER', multiple=True,
    help="Apply advanced filter (see 'pydoc fmf.filter').")
@click.option(
    '-c', '--condition', 'conditions', metavar="EXPR", multiple=True,
    help="Use arbitrary Python expression for filtering.")
@click.option(
    '--link', 'links', metavar="RELATION:TARGET", multiple=True,
    help="Filter by linked objects (regular expressions are "
         "supported for both relation and target).")
@verbose_debug_quiet
def run_tests(context: click.core.Context, **kwargs: Any) -> None:
    """
    Select tests which should be executed.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.base.Test._save_context(context)


# FIXME: click 8.0 renamed resultcallback to result_callback. The former
#        name will be removed in click 8.1. However, click 8.0 will not
#        be added to F33 and F34. Get rid of this workaround once
#        all Fedora + EPEL releases have click 8.0 or newer available.
callback = run.result_callback
if callback is None:
    callback = run.resultcallback


# TODO: commands is unknown, needs revisit
@callback()  # type: ignore
@click.pass_context
def finito(click_context: click.core.Context, commands: Any, *args: Any, **kwargs: Any) -> None:
    """ Run tests if run defined """
    if hasattr(click_context.obj, 'run'):
        click_context.obj.run.go()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Test
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def tests(context: click.core.Context, **kwargs: Any) -> None:
    """
    Manage tests (L1 metadata).

    Check available tests, inspect their metadata.
    Convert old metadata into the new fmf format.
    """

    # Show overview of available tests
    if context.invoked_subcommand is None:
        tmt.Test.overview(context.obj.tree)


@tests.command(name='ls')
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def tests_ls(context: click.core.Context, **kwargs: Any) -> None:
    """
    List available tests.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        test.ls()


@tests.command(name='show')
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def tests_show(context: click.core.Context, **kwargs: Any) -> None:
    """
    Show test details.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        test.show()
        echo()


@tests.command(name='lint')
@click.pass_context
@name_filter_condition
@source
@fix
@verbose_debug_quiet
def tests_lint(context: click.core.Context, **kwargs: Any) -> None:
    """
    Check tests against the L1 metadata specification.

    Regular expression can be used to filter tests for linting.
    Use '.' to select tests under the current working directory.
    """
    # FIXME: Workaround https://github.com/pallets/click/pull/1840 for click 7
    context.params.update(**kwargs)
    tmt.Test._save_context(context)
    exit_code = 0
    for test in context.obj.tree.tests():
        if not test.lint():
            exit_code = 1
        echo()
    raise SystemExit(exit_code)


_test_templates = listed(tmt.templates.TEST, join='or')


@tests.command(name='create')
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    help='Test template ({}).'.format(_test_templates),
    prompt='Template ({})'.format(_test_templates))
@verbose_debug_quiet
@force_dry
def tests_create(
        context: click.core.Context,
        name: str,
        template: str,
        force: bool,
        **kwargs: Any) -> None:
    """
    Create a new test based on given template.

    Specify directory name or use '.' to create tests under the
    current working directory.
    """
    tmt.Test._save_context(context)
    tmt.Test.create(name, template, context.obj.tree.root, force)


@tests.command(name='import')
@click.pass_context
@click.argument('paths', nargs=-1, metavar='[PATH]...')
@click.option(
    '--nitrate / --no-nitrate', default=True,
    help='Import test metadata from Nitrate')
@click.option(
    '--purpose / --no-purpose', default=True,
    help='Migrate description from PURPOSE file')
@click.option(
    '--makefile / --no-makefile', default=True,
    help='Convert Beaker Makefile metadata')
@click.option(
    '--restraint / --no-restraint', default=False,
    help='Convert restraint metadata file')
@click.option(
    '--general / --no-general', default=True,
    help='Detect components from linked nitrate general plans '
         '(overrides Makefile/restraint component).')
@click.option(
    '--type', 'types', metavar='TYPE', default=['multihost'], multiple=True,
    show_default=True,
    help="Convert selected types from Makefile into tags. "
         "Use 'all' to convert all detected types.")
@click.option(
    '--disabled', default=False, is_flag=True,
    help='Import disabled test cases from Nitrate as well.')
@click.option(
    '--manual', default=False, is_flag=True,
    help='Import manual test cases from Nitrate.')
@click.option(
    '--plan', metavar='PLAN', type=int,
    help='Identifier of test plan from which to import manual test cases.')
@click.option(
    '--case', metavar='CASE', type=int,
    help='Identifier of manual test case to be imported.')
@click.option(
    '--with-script', default=False, is_flag=True,
    help='Import manual cases with non-empty script field in Nitrate.')
@verbose_debug_quiet
@force_dry
def tests_import(
        context: click.core.Context,
        paths: List[str],
        makefile: bool,
        restraint: bool,
        general: bool,
        types: List[str],
        nitrate: bool,
        purpose: bool,
        disabled: bool,
        manual: bool,
        plan: int,
        case: int,
        with_script: bool,
        **kwargs: Any) -> None:
    """
    Import old test metadata into the new fmf format.

    Accepts one or more directories where old metadata are stored.
    By default all available sources and current directory are used.
    The following test metadata are converted for each source:

    \b
    makefile ..... summary, component, duration, require
    restraint .... name, description, entry_point, owner,
                   max_time, repoRequires
    purpose ...... description
    nitrate ...... contact, component, tag,
                   environment, relevancy, enabled
    """
    tmt.Test._save_context(context)

    if manual:
        if not (case or plan):
            raise tmt.utils.GeneralError(
                "Option --case or --plan is mandatory when using --manual.")
        else:
            tmt.convert.read_manual(plan, case, disabled, with_script)
            return

    if not paths:
        paths = ['.']
    for path in paths:
        # Make sure we've got a real directory
        path = os.path.realpath(path)
        if not os.path.isdir(path):
            raise tmt.utils.GeneralError(
                "Path '{0}' is not a directory.".format(path))
        # Gather old metadata and store them as fmf
        common, individual = tmt.convert.read(
            path, makefile, restraint, nitrate, purpose, disabled, types,
            general)
        # Add path to common metadata if there are virtual test cases
        if individual:
            root = fmf.Tree(path).root
            common['path'] = os.path.join('/', os.path.relpath(path, root))
        # Store common metadata
        common_path = os.path.join(path, 'main.fmf')
        tmt.convert.write(common_path, common)
        # Store individual data (as virtual tests)
        for testcase in individual:
            testcase_path = os.path.join(
                path, str(testcase['extra-nitrate']) + '.fmf')
            tmt.convert.write(testcase_path, testcase)
        # Adjust runtest.sh content and permission if needed
        tmt.convert.adjust_runtest(os.path.join(path, 'runtest.sh'))


@tests.command(name='export')
@click.pass_context
@name_filter_condition_long
@click.option(
    '-h', '--how', metavar='METHOD',
    help='Use specified method for export (nitrate or polarion).')
@click.option(
    '--nitrate', is_flag=True,
    help="Export test metadata to Nitrate, deprecated by '--how nitrate'.")
@click.option(
    '--project-id', help='Use specific Polarion project ID.')
@click.option(
    '--bugzilla', is_flag=True,
    help="Link Nitrate case to Bugzilla specified in the 'link' attribute "
         "with the relation 'verifies'.")
@click.option(
    '--ignore-git-validation', is_flag=True,
    help="Ignore unpublished git changes and export to Nitrate. "
    "The case might not be able to be scheduled!")
@click.option(
    '--create', is_flag=True,
    help="Create test cases in nitrate if they don't exist.")
@click.option(
    '--general / --no-general', default=False,
    help="Link Nitrate case to component's General plan. Disabled by default. "
         "Note that this will unlink any previously connected general plans.")
@click.option(
    '--link-runs / --no-link-runs', default=False,
    help="Link Nitrate case to all open runs of descendant plans of "
         "General plan. Disabled by default. Implies --general option.")
@click.option(
    '--format', 'format_', default='yaml', show_default=True, metavar='FORMAT',
    help='Output format (yaml or dict).')
@click.option(
    '--fmf-id', is_flag=True,
    help='Show fmf identifiers instead of test metadata.')
@click.option(
    '--duplicate / --no-duplicate', default=False, show_default=True,
    help='Allow or prevent creating duplicates in Nitrate by searching for '
         'existing test cases with the same fmf identifier.')
@click.option(
    '-n', '--dry', is_flag=True,
    help="Run in dry mode. No changes, please.")
@click.option(
    '-d', '--debug', is_flag=True,
    help='Provide as much debugging details as possible.')
def tests_export(
        context: click.core.Context,
        format_: str,
        how: str,
        nitrate: bool,
        bugzilla: bool,
        **kwargs: Any) -> None:
    """
    Export test data into the desired format.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    if nitrate:
        context.obj.common.warn(
            "Option '--nitrate' is deprecated, please use '--how nitrate' instead.")
        how = 'nitrate'
    if bugzilla and not how:
        raise tmt.utils.GeneralError(
            "The --bugzilla option is supported only with --nitrate "
            "or --polarion for now.")

    if how == 'nitrate' or how == 'polarion':
        for test in context.obj.tree.tests():
            test.export(format_=how)
    elif format_ in ['dict', 'yaml']:
        keys = None
        if kwargs.get('fmf_id'):
            keys = 'fmf-id'

        tests = [test.export(format_='dict', keys=keys) for test in
                 context.obj.tree.tests()]
        if format_ == 'dict':
            echo(tests, nl=False)
        else:
            echo(tmt.utils.dict_to_yaml(tests), nl=False)
    else:
        raise tmt.utils.GeneralError(
            f"Invalid test export format '{format_}'.")


@tests.command(name="id")
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
@force_dry
def tests_id(context: click.core.Context, **kwargs: Any) -> None:
    """
    Generate a unique id for each selected test.

    A new UUID is generated for each test matching the provided
    filter and the value is stored to disk. Existing identifiers
    are kept intact.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        tmt.identifier.id_command(test.node, "test", dry=kwargs["dry"])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Plan
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def plans(context: click.core.Context, **kwargs: Any) -> None:
    """
    Manage test plans (L2 metadata).

    \b
    Search for available plans.
    Explore detailed test step configuration.
    """
    tmt.Plan._save_context(context)

    # Show overview of available plans
    if context.invoked_subcommand is None:
        tmt.Plan.overview(context.obj.tree)


@plans.command(name='ls')
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def plans_ls(context: click.core.Context, **kwargs: Any) -> None:
    """
    List available plans.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        plan.ls()


@plans.command(name='show')
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def plans_show(context: click.core.Context, **kwargs: Any) -> None:
    """
    Show plan details.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        plan.show()
        echo()


@plans.command(name='lint')
@click.pass_context
@name_filter_condition
@source
@verbose_debug_quiet
def plans_lint(context: click.core.Context, **kwargs: Any) -> None:
    """
    Check plans against the L2 metadata specification.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    # FIXME: Workaround https://github.com/pallets/click/pull/1840 for click 7
    context.params.update(**kwargs)
    tmt.Plan._save_context(context)
    exit_code = 0
    for plan in context.obj.tree.plans():
        if not plan.lint():
            exit_code = 1
        echo()
    raise SystemExit(exit_code)


_plan_templates = listed(tmt.templates.PLAN, join='or')


@plans.command(name='create')
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    help='Plan template ({}).'.format(_plan_templates),
    prompt='Template ({})'.format(_plan_templates))
@click.option(
    '--discover', metavar='YAML', multiple=True,
    help='Discover phase content in yaml format.')
@click.option(
    '--provision', metavar='YAML', multiple=True,
    help='Provision phase content in yaml format.')
@click.option(
    '--prepare', metavar='YAML', multiple=True,
    help='Prepare phase content in yaml format.')
@click.option(
    '--execute', metavar='YAML', multiple=True,
    help='Execute phase content in yaml format.')
@click.option(
    '--report', metavar='YAML', multiple=True,
    help='Report phase content in yaml format.')
@click.option(
    '--finish', metavar='YAML', multiple=True,
    help='Finish phase content in yaml format.')
@verbose_debug_quiet
@force_dry
def plans_create(
        context: click.core.Context,
        name: str,
        template: str,
        force: bool,
        **kwargs: Any) -> None:
    """ Create a new plan based on given template. """
    tmt.Plan._save_context(context)
    tmt.Plan.create(name, template, context.obj.tree.root, force)


@plans.command(name='export')
@click.pass_context
@name_filter_condition_long
@click.option(
    '--format', 'format_', default='yaml', show_default=True, metavar='FORMAT',
    help='Output format.')
@click.option(
    '-d', '--debug', is_flag=True,
    help='Provide as much debugging details as possible.')
def plans_export(context: click.core.Context, format_: str, **kwargs: Any) -> None:
    """
    Export plans into desired format.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    plans = [plan.export(format_='dict') for plan in context.obj.tree.plans()]

    # Choose proper format
    if format_ == 'dict':
        echo(plans)
    elif format_ == 'yaml':
        echo(tmt.utils.dict_to_yaml(plans))
    else:
        raise tmt.utils.GeneralError(
            f"Invalid plan export format '{format_}'.")


@plans.command(name="id")
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
@force_dry
def plans_id(context: click.core.Context, **kwargs: Any) -> None:
    """
    Generate a unique id for each selected plan.

    A new UUID is generated for each plan matching the provided
    filter and the value is stored to disk. Existing identifiers
    are kept intact.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        tmt.identifier.id_command(plan.node, "plan", dry=kwargs["dry"])

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def stories(context: click.core.Context, **kwargs: Any) -> None:
    """
    Manage user stories.

    \b
    Check available user stories.
    Explore coverage (test, implementation, documentation).
    """
    tmt.Story._save_context(context)

    # Show overview of available stories
    if context.invoked_subcommand is None:
        tmt.Story.overview(context.obj.tree)


@stories.command(name='ls')
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@verbose_debug_quiet
def stories_ls(
        context: click.core.Context,
        implemented: bool,
        verified: bool,
        documented: bool,
        covered: bool,
        unimplemented: bool,
        unverified: bool,
        undocumented: bool,
        uncovered: bool,
        **kwargs: Any) -> None:
    """
    List available stories.

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)
    for story in context.obj.tree.stories():
        if story._match(implemented, verified, documented, covered,
                        unimplemented, unverified, undocumented, uncovered):
            story.ls()


@stories.command(name='show')
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@verbose_debug_quiet
def stories_show(
        context: click.core.Context,
        implemented: bool,
        verified: bool,
        documented: bool,
        covered: bool,
        unimplemented: bool,
        unverified: bool,
        undocumented: bool,
        uncovered: bool,
        **kwargs: Any) -> None:
    """
    Show story details.

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)
    for story in context.obj.tree.stories():
        if story._match(implemented, verified, documented, covered,
                        unimplemented, unverified, undocumented, uncovered):
            story.show()
            echo()


_story_templates = listed(tmt.templates.STORY, join='or')


@stories.command(name='create')
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    prompt='Template ({})'.format(_story_templates),
    help='Story template ({}).'.format(_story_templates))
@verbose_debug_quiet
@force_dry
def stories_create(
        context: click.core.Context,
        name: str,
        template: str,
        force: bool,
        **kwargs: Any) -> None:
    """ Create a new story based on given template. """
    tmt.Story._save_context(context)
    tmt.base.Story.create(name, template, context.obj.tree.root, force)


@stories.command(name='coverage')
@click.option(
    '--docs', is_flag=True, help='Show docs coverage.')
@click.option(
    '--test', is_flag=True, help='Show test coverage.')
@click.option(
    '--code', is_flag=True, help='Show code coverage.')
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@verbose_debug_quiet
def stories_coverage(
        context: click.core.Context,
        code: bool,
        test: bool,
        docs: bool,
        implemented: bool,
        verified: bool,
        documented: bool,
        covered: bool,
        unimplemented: bool,
        unverified: bool,
        undocumented: bool,
        uncovered: bool,
        **kwargs: Any) -> None:
    """
    Show code, test and docs coverage for given stories.

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)

    def headfoot(text: str) -> None:
        """ Format simple header/footer """
        echo(style(text.rjust(4) + ' ', fg='blue'), nl=False)

    header = False
    total = code_coverage = test_coverage = docs_coverage = 0
    if not any([code, test, docs]):
        code = test = docs = True
    for story in context.obj.tree.stories():
        # Check conditions
        if not story._match(
                implemented, verified, documented, covered, unimplemented,
                unverified, undocumented, uncovered):
            continue
        # Show header once
        if not header:
            if code:
                headfoot('code')
            if test:
                headfoot('test')
            if docs:
                headfoot('docs')
            headfoot('story')
            echo()
            header = True
        # Show individual stats
        status = story.coverage(code, test, docs)
        total += 1
        code_coverage += status[0]
        test_coverage += status[1]
        docs_coverage += status[2]
    # Summary
    if not total:
        return
    if code:
        headfoot('{}%'.format(round(100 * code_coverage / total)))
    if test:
        headfoot('{}%'.format(round(100 * test_coverage / total)))
    if docs:
        headfoot('{}%'.format(round(100 * docs_coverage / total)))
    headfoot('from {}'.format(listed(total, 'story')))
    echo()


@stories.command(name='export')
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@click.option(
    '--format', 'format_', default='rst', show_default=True, metavar='FORMAT',
    help='Output format.')
@click.option(
    '-d', '--debug', is_flag=True,
    help='Provide as much debugging details as possible.')
def stories_export(
        context: click.core.Context,
        format_: str,
        implemented: bool,
        verified: bool,
        documented: bool,
        covered: bool,
        unimplemented: bool,
        unverified: bool,
        undocumented: bool,
        uncovered: bool,
        **kwargs: Any) -> None:
    """
    Export selected stories into desired format.

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)

    for story in context.obj.tree.stories(whole=True):
        if story._match(implemented, verified, documented, covered,
                        unimplemented, unverified, undocumented, uncovered):
            echo(story.export(format_))


@stories.command(name='lint')
@click.pass_context
@name_filter_condition
@source
@verbose_debug_quiet
def stories_lint(context: click.core.Context, **kwargs: Any) -> None:
    """
    Check stories against the L3 metadata specification.

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    # FIXME: Workaround https://github.com/pallets/click/pull/1840 for click 7
    context.params.update(**kwargs)
    tmt.Story._save_context(context)
    exit_code = 0
    for story in context.obj.tree.stories():
        if not story.lint():
            exit_code = 1
        echo()
    raise SystemExit(exit_code)


@stories.command(name="id")
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@verbose_debug_quiet
@force_dry
def stories_id(
        context: click.core.Context,
        implemented: bool,
        verified: bool,
        documented: bool,
        covered: bool,
        unimplemented: bool,
        unverified: bool,
        undocumented: bool,
        uncovered: bool,
        **kwargs: Any) -> None:
    """
    Generate a unique id for each selected story.

    A new UUID is generated for each story matching the provided
    filter and the value is stored to disk. Existing identifiers
    are kept intact.
    """
    tmt.Story._save_context(context)
    for story in context.obj.tree.stories():
        if story._match(implemented, verified, documented, covered,
                        unimplemented, unverified, undocumented, uncovered):
            tmt.identifier.id_command(story.node, "story", dry=kwargs["dry"])


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Init
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.command()
@click.pass_context
@click.argument('path', default='.')
@click.option(
    '-t', '--template', default='empty', metavar='TEMPLATE',
    type=click.Choice(['empty'] + tmt.templates.INIT_TEMPLATES),
    help='Template ({}).'.format(
        listed(tmt.templates.INIT_TEMPLATES, join='or')))
@verbose_debug_quiet
@force_dry
def init(
        context: click.core.Context,
        path: str,
        template: str,
        force: bool,
        **kwargs: Any) -> None:
    """
    Initialize a new tmt tree.

    By default tree is created in the current directory.
    Provide a PATH to create it in a different location.

    \b
    A tree can be optionally populated with example metadata:
    * 'mini' template contains a minimal plan and no tests,
    * 'base' template contains a plan and a beakerlib test,
    * 'full' template contains a 'full' story, an 'full' plan and a shell test.
    """

    tmt.base.Tree._save_context(context)
    tmt.base.Tree.init(path, template, force, **kwargs)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Status
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.command()
@click.pass_context
@click.argument('path', default=tmt.utils.WORKDIR_ROOT)
@click.option(
    '-i', '--id', metavar="ID",
    help='Run id (name or directory path) to show status of.')
@click.option(
    '--abandoned', is_flag=True, default=False,
    help='List runs which have provision step completed but finish step '
         'not yet done.')
@click.option(
    '--active', is_flag=True, default=False,
    help='List runs where at least one of the enabled steps has not '
         'been finished.')
@click.option(
    '--finished', is_flag=True, default=False,
    help='List all runs which have all enabled steps completed.')
@verbose_debug_quiet
def status(
        context: click.core.Context,
        path: str,
        abandoned: bool,
        active: bool,
        finished: bool,
        **kwargs: Any) -> None:
    """
    Show status of runs.

    Lists past runs in the given directory filtered using options.
    /var/tmp/tmt is used by default.

    By default, status of the whole runs is listed. With more
    verbosity (-v), status of every plan is shown. By default,
    the last completed step is displayed, 'done' is used when
    all enabled steps are completed. Status of every step is
    displayed with the most verbosity (-vv).

    """
    if [abandoned, active, finished].count(True) > 1:
        raise tmt.utils.GeneralError(
            "Options --abandoned, --active and --finished cannot be "
            "used together.")
    if not os.path.exists(path):
        raise tmt.utils.GeneralError(f"Path '{path}' doesn't exist.")
    status_obj = tmt.Status(context=context)
    status_obj.show()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Clean
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

dry = tmt.options.force_dry[1]


@main.group(chain=True, invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
@dry
def clean(context: click.core.Context, **kwargs: Any) -> None:
    """
    Clean workdirs, guests or images.

    Without any command, clean everything, stop the guests, remove
    all runs and then remove all images. Search for runs in
    /var/tmp/tmt, if runs are stored elsewhere, the path to them can
    be set using a subcommand (either runs or guests subcommand).
    """
    clean_obj = tmt.Clean(parent=context.obj.common, context=context)
    context.obj.clean = clean_obj
    exit_code = 0
    if context.invoked_subcommand is None:
        echo(style('clean', fg='red'))
        # Set path to default
        context.params['path'] = tmt.utils.WORKDIR_ROOT
        # Create another level to the hierarchy so that logging indent is
        # consistent between the command and subcommands
        clean_obj = tmt.Clean(parent=clean_obj, context=context)
        if os.path.exists(tmt.utils.WORKDIR_ROOT):
            if not clean_obj.guests():
                exit_code = 1
            if not clean_obj.runs():
                exit_code = 1
        else:
            clean_obj.warn(
                f"Directory '{tmt.utils.WORKDIR_ROOT}' does not exist, "
                f"skipping guest and run cleanup.")
        clean_obj.images()
        raise SystemExit(exit_code)


@clean.command(name='runs')
@click.pass_context
@click.argument('path', default=tmt.utils.WORKDIR_ROOT)
@click.option(
    '-l', '--last', is_flag=True, help='Clean the workdir of the last run.')
@click.option(
    '-i', '--id', 'id_', metavar="ID",
    help='Run id (name or directory path) to clean workdir of.')
@click.option(
    '-k', '--keep', type=int,
    help='The number of latest workdirs to keep, clean the rest.')
@verbose_debug_quiet
@dry
def clean_runs(
        context: click.core.Context,
        path: str,
        last: bool,
        id_: str,
        keep: int,
        **kwargs: Any) -> None:
    """
    Clean workdirs of past runs.

    Remove all runs in /var/tmp/tmt by default. Path to where runs
    should be searched can be specified using PATH argument.
    """
    echo(style('clean', fg='red'))
    defined = [last is True, id_ is not None, keep is not None]
    if defined.count(True) > 1:
        raise tmt.utils.GeneralError(
            "Options --last, --id and --keep cannot be used together.")
    if keep is not None and keep < 0:
        raise tmt.utils.GeneralError("--keep must not be a negative number.")
    if not os.path.exists(path):
        raise tmt.utils.GeneralError(f"Path '{path}' doesn't exist.")
    exit_code = 0
    if not tmt.Clean(parent=context.obj.clean, context=context).runs():
        exit_code = 1
    raise SystemExit(exit_code)


@clean.command(name='guests')
@click.pass_context
@click.argument('path', default=tmt.utils.WORKDIR_ROOT)
@click.option(
    '-l', '--last', is_flag=True, help='Stop the guest of the last run.')
@click.option(
    '-i', '--id', 'id_', metavar="ID",
    help='Run id (name or directory path) to stop the guest of.')
@click.option(
    '-h', '--how', metavar='METHOD',
    help='Stop guests of the specified provision method.')
@verbose_debug_quiet
@dry
def clean_guests(
        context: click.core.Context,
        path: str,
        last: bool,
        id_: int,
        **kwargs: Any) -> None:
    """
    Stop running guests of runs.

    Stop guests of all runs in /var/tmp/tmt by default. Path to where
    runs should be searched can be specified using PATH argument.
    """
    echo(style('clean', fg='red'))
    if last and id_ is not None:
        raise tmt.utils.GeneralError(
            "Options --last and --id cannot be used together.")
    if not os.path.exists(path):
        raise tmt.utils.GeneralError(f"Path '{path}' doesn't exist.")
    exit_code = 0
    if not tmt.Clean(parent=context.obj.clean, context=context).guests():
        exit_code = 1
    raise SystemExit(exit_code)


@clean.command(name='images')
@click.pass_context
@verbose_debug_quiet
@dry
def clean_images(context: click.core.Context, **kwargs: Any) -> None:
    """
    Remove images of supported provision methods.

    Currently supported methods are:
     - testcloud
    """
    echo(style('clean', fg='red'))
    # FIXME: If there are more provision methods supporting this,
    #        we should add options to specify which provision should be
    #        cleaned, similarly to guests.
    tmt.Clean(parent=context.obj.clean, context=context).images()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Lint
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@main.command(name='lint')
@click.pass_context
@name_filter_condition
@source
@fix
@verbose_debug_quiet
def lint(context: click.core.Context, **kwargs: Any) -> None:
    """
    Check all the present metadata against the specification.

    Combines all the partial linting (tests, plans and stories)
    into one command. Options are applied to all parts of the lint.

    Regular expression can be used to filter metadata by name.
    Use '.' to select tests, plans and stories under the current
    working directory.
    """
    exit_code = 0
    for command in (tests_lint, plans_lint, stories_lint):
        try:
            context.forward(command)
        except SystemExit as e:
            exit_code |= e.code
    raise SystemExit(exit_code)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Setup
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


@main.group(cls=CustomGroup)
@click.pass_context
def setup(context: click.core.Context, **kwargs: Any) -> None:
    """
    Setup the environment for working with tmt.
    """


@setup.group(cls=CustomGroup)
@click.pass_context
def completion(context: click.core.Context, **kwargs: Any) -> None:
    """
    Setup shell completions.

    By default, these commands only write a shell script to the output
    which can then be sourced from the shell's configuration file. Use
    the '--install' option to store and enable the configuration
    permanently.
    """


COMPLETE_VARIABLE = '_TMT_COMPLETE'
COMPLETE_SCRIPT = 'tmt-complete'


def setup_completion(shell: str, install: bool) -> None:
    """ Setup completion based on the shell """
    config = tmt.utils.Config()
    # Fish gets installed into its special location where it is automatically
    # loaded.
    if shell == 'fish':
        script = os.path.expanduser('~/.config/fish/completions/tmt.fish')
    # Bash and zsh get installed to tmt's config directory.
    else:
        script = os.path.join(config.path, f'{COMPLETE_SCRIPT}.{shell}')

    out = open(script, 'w') if install else sys.stdout
    subprocess.run(f'{COMPLETE_VARIABLE}={shell}_source tmt',
                   shell=True, stdout=out)

    if install:
        out.close()
        # If requested, modify .bashrc or .zshrc
        if shell != 'fish':
            config_path = os.path.expanduser(f'~/.{shell}rc')
            with open(config_path, 'a') as shell_config:
                shell_config.write('\n# Generated by tmt\n')
                shell_config.write(f'source {script}')


@completion.command(name='bash')
@click.pass_context
@click.option(
    '--install', '-i', 'install', is_flag=True,
    help="Persistently store the script to tmt's configuration directory "
         "and set it up by modifying '~/.bashrc'.")
def completion_bash(context: click.core.Context, install: bool, **kwargs: Any) -> None:
    """
    Setup shell completions for bash.
    """
    setup_completion('bash', install)


@completion.command(name='zsh')
@click.pass_context
@click.option(
    '--install', '-i', 'install', is_flag=True,
    help="Persistently store the script to tmt's configuration directory "
         "and set it up by modifying '~/.zshrc'.")
def completion_zsh(context: click.core.Context, install: bool, **kwargs: Any) -> None:
    """
    Setup shell completions for zsh.
    """
    setup_completion('zsh', install)


@completion.command(name='fish')
@click.pass_context
@click.option(
    '--install', '-i', 'install', is_flag=True,
    help="Persistently store the script to "
         "'~/.config/fish/completions/tmt.fish'.")
def completion_fish(context: click.core.Context, install: bool, **kwargs: Any) -> None:
    """
    Setup shell completions for fish.
    """
    setup_completion('fish', install)
