# coding: utf-8

""" Command line interface for the Test Management Tool """

from click import echo, style
from fmf.utils import listed

import click
import os

import fmf
import tmt
import tmt.utils
import tmt.plugins
import tmt.convert
import tmt.export
import tmt.steps
import tmt.templates
import tmt.options

# Explore available plugins (need to detect all supported methods first)
tmt.plugins.explore()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Custom Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CustomGroup(click.Group):
    """ Custom Click Group """

    def list_commands(self, context):
        """ Prevent alphabetical sorting """
        return self.commands.keys()

    def get_command(self, context, cmd_name):
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

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Common Options
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def verbose_debug_quiet(function):
    """ Verbose, debug and quiet output """
    for option in reversed(tmt.options.verbose_debug_quiet):
        function = option(function)
    return function


def force_dry(function):
    """ Force and dry actions """
    for option in reversed(tmt.options.force_dry):
        function = option(function)
    return function


def name_filter_condition(function):
    """ Common filter options (short & long) """
    options = [
        click.argument(
            'names', nargs=-1, metavar='[REGEXP]'),
        click.option(
            '-f', '--filter', 'filters', metavar='FILTER', multiple=True,
            help="Apply advanced filter (see 'pydoc fmf.filter')."),
        click.option(
            '-c', '--condition', 'conditions', metavar="EXPR", multiple=True,
            help="Use arbitrary Python expression for filtering."),
        ]

    for option in reversed(options):
        function = option(function)
    return function


def name_filter_condition_long(function):
    """ Common filter options (long only) """
    options = [
        click.argument(
            'names', nargs=-1, metavar='[REGEXP]'),
        click.option(
            '--filter', 'filters', metavar='FILTER', multiple=True,
            help="Apply advanced filter (see 'pydoc fmf.filter')."),
        click.option(
            '--condition', 'conditions', metavar="EXPR", multiple=True,
            help="Use arbitrary Python expression for filtering."),
        ]

    for option in reversed(options):
        function = option(function)
    return function


def implemented_verified_documented(function):
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
    '-c', '--context', metavar='DATA', multiple='True',
    help='Set the fmf context. Use KEY=VAL or KEY=VAL1,VAL2... format '
         'to define individual dimensions or the @FILE notation to load data '
         'from provided yaml file. Can be specified multiple times. ')
@verbose_debug_quiet
@click.option(
    '--version', is_flag=True,
    help='Show tmt version and commit hash.')
def main(click_contex, root, context, **kwargs):
    """ Test Management Tool """
    # Show current tmt version and exit
    if kwargs.get('version'):
        print(f"tmt version: {tmt.__version__}")
        raise SystemExit(0)

    # Save click context and fmf context for future use
    tmt.utils.Common._save_context(click_contex)
    click_contex.obj = tmt.utils.Common()
    click_contex.obj.fmf_context = tmt.utils.context_to_dict(context)

    # Initialize metadata tree (from given path or current directory)
    tree = tmt.Tree(root or os.curdir)
    click_contex.obj.tree = tree

    # List of enabled steps
    click_contex.obj.steps = set()

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
    help='Enable all steps before the given one.')
@click.option(
    '-B', '--before', type=click.Choice(tmt.steps.STEPS), metavar='STEP',
    help='Enable all steps after the given one.')
@click.option(
    '-S', '--skip', type=click.Choice(tmt.steps.STEPS), metavar='STEP',
    help='Skip given step(s) during test run execution.', multiple=True)
@click.option(
    '-e', '--environment', metavar='KEY=VALUE|@FILE', multiple='True',
    help='Set environment variable. Can be specified multiple times. '
         'The "@" prefix marks a YAML file to load.')
@verbose_debug_quiet
@force_dry
def run(context, id_, **kwargs):
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


@run.command()
@click.pass_context
@click.option(
    '-n', '--name', 'names', metavar='REGEXP', multiple=True,
    help="Regular expression to match plan name.")
@click.option(
    '-f', '--filter', 'filters', metavar='FILTER', multiple=True,
    help="Apply advanced filter (see 'pydoc fmf.filter').")
@click.option(
    '-c', '--condition', 'conditions', metavar="EXPR", multiple=True,
    help="Use arbitrary Python expression for filtering.")
@verbose_debug_quiet
def plans(context, **kwargs):
    """
    Select plans which should be executed.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.base.Plan._save_context(context)


@run.command()
@click.pass_context
@click.option(
    '-n', '--name', 'names', metavar='REGEXP', multiple=True,
    help="Regular expression to match test name.")
@click.option(
    '-f', '--filter', 'filters', metavar='FILTER', multiple=True,
    help="Apply advanced filter (see 'pydoc fmf.filter').")
@click.option(
    '-c', '--condition', 'conditions', metavar="EXPR", multiple=True,
    help="Use arbitrary Python expression for filtering.")
@verbose_debug_quiet
def tests(context, **kwargs):
    """
    Select tests which should be executed.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.base.Test._save_context(context)


@run.resultcallback()
@click.pass_context
def finito(click_context, commands, *args, **kwargs):
    """ Run tests if run defined """
    if hasattr(click_context.obj, 'run'):
        click_context.obj.run.go()

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Test
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def tests(context, **kwargs):
    """
    Manage tests (L1 metadata).

    Check available tests, inspect their metadata.
    Convert old metadata into the new fmf format.
    """

    # Show overview of available tests
    if context.invoked_subcommand is None:
        tmt.Test.overview(context.obj.tree)


@tests.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def ls(context, **kwargs):
    """
    List available tests.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        test.ls()


@tests.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def show(context, **kwargs):
    """
    Show test details.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        test.show()
        echo()


@tests.command()
@click.pass_context
@name_filter_condition
@click.option(
    '-f', '--fix', is_flag=True,
    help='Attempt to fix all discovered issues.')
@verbose_debug_quiet
def lint(context, **kwargs):
    """
    Check tests against the L1 metadata specification.

    Regular expression can be used to filter tests for linting.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    exit_code = 0
    for test in context.obj.tree.tests():
        if not test.lint():
            exit_code = 1
        echo()
    raise SystemExit(exit_code)


_test_templates = listed(tmt.templates.TEST, join='or')
@tests.command()
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    help='Test template ({}).'.format(_test_templates),
    prompt='Template ({})'.format(_test_templates))
@verbose_debug_quiet
@force_dry
def create(context, name, template, force, **kwargs):
    """
    Create a new test based on given template.

    Specify directory name or use '.' to create tests under the
    current working directory.
    """
    tmt.Test._save_context(context)
    tmt.Test.create(name, template, context.obj.tree, force)


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
    '--disabled', default=False, is_flag=True,
    help='Import disabled test cases from Nitrate as well.')
@click.option(
    '--manual', default=False, is_flag=True,
    help='Import manual test cases from Nitrate.')
@click.option(
    '--plan', metavar='PLAN',
    help='Identifier of test plan from which to import manual test cases.')
@click.option(
    '--case', metavar='CASE',
    help='Identifier of manual test case to be imported.')
@click.option(
    '--with-script', default=False, is_flag=True,
    help='Import manual cases with non-empty script field in Nitrate.')
@verbose_debug_quiet
@force_dry
def import_(
        context, paths, makefile, nitrate, purpose, disabled, manual, plan,
        case, with_script, **kwargs):
    """
    Import old test metadata into the new fmf format.

    Accepts one or more directories where old metadata are stored.
    By default all available sources and current directory are used.
    The following test metadata are converted for each source:

    \b
    makefile ..... summary, component, duration, require
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
            return 0

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
            path, makefile, nitrate, purpose, disabled)
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


@tests.command()
@click.pass_context
@name_filter_condition_long
@click.option(
    '--nitrate', is_flag=True,
    help='Export test metadata to Nitrate.')
@click.option(
    '--create', is_flag=True,
    help="Create test cases in nitrate if they don't exist.")
@click.option(
    '--general / --no-general', default=True,
    help="Link Nitrate case to component's General plan.")
@click.option(
    '--format', 'format_', default='yaml', show_default=True, metavar='FORMAT',
    help='Output format.')
@click.option(
    '-d', '--debug', is_flag=True,
    help='Provide as much debugging details as possible.')
def export(context, format_, nitrate, create, general, **kwargs):
    """
    Export test data into the desired format.

    Regular expression can be used to filter tests by name.
    Use '.' to select tests under the current working directory.
    """
    tmt.Test._save_context(context)
    for test in context.obj.tree.tests():
        if nitrate:
            test.export(format_='nitrate', create=create, general=general)
        else:
            echo(test.export(format_=format_))


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Plan
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def plans(context, **kwargs):
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


@plans.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def ls(context, **kwargs):
    """
    List available plans.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        plan.ls()


@plans.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def show(context, **kwargs):
    """
    Show plan details.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    for plan in context.obj.tree.plans():
        plan.show()
        echo()


@plans.command()
@click.pass_context
@name_filter_condition
@verbose_debug_quiet
def lint(context, **kwargs):
    """
    Check plans against the L2 metadata specification.

    Regular expression can be used to filter plans by name.
    Use '.' to select plans under the current working directory.
    """
    tmt.Plan._save_context(context)
    exit_code = 0
    for plan in context.obj.tree.plans():
        if not plan.lint():
            exit_code = 1
        echo()
    raise SystemExit(exit_code)


_plan_templates = listed(tmt.templates.PLAN, join='or')
@plans.command()
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
def create(context, name, template, force, **kwargs):
    """ Create a new plan based on given template. """
    tmt.Plan._save_context(context)
    tmt.Plan.create(name, template, context.obj.tree, force)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Story
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.group(invoke_without_command=True, cls=CustomGroup)
@click.pass_context
@verbose_debug_quiet
def stories(context, **kwargs):
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


@stories.command()
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@verbose_debug_quiet
def ls(
    context, implemented, verified, documented, covered,
    unimplemented, unverified, undocumented, uncovered, **kwargs):
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


@stories.command()
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@verbose_debug_quiet
def show(
    context, implemented, verified, documented, covered,
    unimplemented, unverified, undocumented, uncovered, **kwargs):
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
@stories.command()
@click.pass_context
@click.argument('name')
@click.option(
    '-t', '--template', metavar='TEMPLATE',
    prompt='Template ({})'.format(_story_templates),
    help='Story template ({}).'.format(_story_templates))
@verbose_debug_quiet
@force_dry
def create(context, name, template, force, **kwargs):
    """ Create a new story based on given template. """
    tmt.Story._save_context(context)
    tmt.base.Story.create(name, template, context.obj.tree, force)


@stories.command()
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
def coverage(
    context, code, test, docs,
    implemented, verified, documented, covered,
    unimplemented, unverified, undocumented, uncovered, **kwargs):
    """
    Show code, test and docs coverage for given stories.

    Regular expression can be used to filter stories by name.
    Use '.' to select stories under the current working directory.
    """
    tmt.Story._save_context(context)

    def headfoot(text):
        """ Format simple header/footer """
        echo(style(text.rjust(4) + ' ', fg='blue'), nl=False)

    header = False
    total = code_coverage = test_coverage = docs_coverage = 0
    if not any([code, test, docs]):
        code = test = docs = True
    for story in context.obj.tree.stories():
        # Check conditions
        if not story._match(implemented, verified, documented, covered,
                unimplemented, unverified, undocumented, uncovered):
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


@stories.command()
@click.pass_context
@name_filter_condition_long
@implemented_verified_documented
@click.option(
    '--format', 'format_', default='rst', show_default=True, metavar='FORMAT',
    help='Output format.')
@click.option(
    '-d', '--debug', is_flag=True,
    help='Provide as much debugging details as possible.')
def export(
    context, format_,
    implemented, verified, documented, covered,
    unimplemented, unverified, undocumented, uncovered, **kwargs):
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


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Init
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

_init_template_choices = ['empty', 'mini', 'base', 'full']
_init_templates = listed(_init_template_choices, join='or')
@main.command()
@click.pass_context
@click.argument('path', default='.')
@click.option(
    '-t', '--template', default='empty', metavar='TEMPLATE',
    type=click.Choice(_init_template_choices),
    help='Template ({}).'.format(_init_templates))
@verbose_debug_quiet
@force_dry
def init(context, path, template, force, **kwargs):
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

    # Check for existing tree
    path = os.path.realpath(path)
    try:
        tree = tmt.Tree(path)
        # Are we creating a new tree under the existing one?
        if path == tree.root:
            echo("Tree '{}' already exists.".format(tree.root))
        else:
            tree = None
    except tmt.utils.GeneralError:
        tree = None
    # Create a new tree
    if tree is None:
        try:
            fmf.Tree.init(path)
            tree = tmt.Tree(path)
        except fmf.utils.GeneralError as error:
            raise tmt.utils.GeneralError(
                "Failed to initialize tree in '{}': {}".format(
                    path, error))
        echo("Tree '{}' initialized.".format(tree.root))

    # Populate the tree with example objects if requested
    if template == 'empty':
        non_empty_choices = [c for c in _init_template_choices if c != 'empty']
        echo("To populate it with example content, use --template with "
             "{}.".format(listed(non_empty_choices, join='or')))
    else:
        echo("Applying template '{}'.".format(template, _init_templates))
    if template == 'mini':
        tmt.Plan.create('/plans/example', 'mini', tree, force)
    elif template == 'base':
        tmt.Test.create('/tests/example', 'beakerlib', tree, force)
        tmt.Plan.create('/plans/example', 'base', tree, force)
    elif template == 'full':
        tmt.Test.create('/tests/example', 'shell', tree, force)
        tmt.Plan.create('/plans/example', 'full', tree, force)
        tmt.Story.create('/stories/example', 'full', tree, force)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Status
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@main.command()
@click.pass_context
@click.argument('path', default=tmt.utils.WORKDIR_ROOT)
@click.option(
    '-i', '--id', help=
    'Run id (name or directory path) to show status of.', metavar="ID")
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
def status(context, path, abandoned, active, finished, **kwargs):
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
        raise tmt.utils.GeneralError(f"Path {path} doesn't exist.")
    status_obj = tmt.Status(context=context)
    status_obj.show()
