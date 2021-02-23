# coding: utf-8

""" Convert metadata into the new format """

from io import open
from click import echo, style
from tmt.utils import ConvertError, StructuredFieldError

import fmf.utils
import tmt.utils
import subprocess
import pprint
import copy
import yaml
import re
import os

log = fmf.utils.Logging('tmt').logger


# Test case relevancy regular expressions
RELEVANCY_COMMENT =  r"^([^#]*?)\s*#\s*(.+)$"
RELEVANCY_RULE = r"^([^:]+)\s*:\s*(.+)$"
RELEVANCY_EXPRESSION = (
    r"^\s*(.*?)\s*(!?contains|!?defined|[=<>!]+)\s*(.*?)\s*$")


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  YAML
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Special hack to store multiline text with the '|' style
# See https://stackoverflow.com/questions/45004464/
# Python 2 version
try:
    yaml.SafeDumper.orig_represent_unicode = yaml.SafeDumper.represent_unicode
    def repr_unicode(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar(
                u'tag:yaml.org,2002:str', data, style='|')
        return dumper.orig_represent_unicode(data)
    yaml.add_representer(unicode, repr_unicode, Dumper=yaml.SafeDumper)
# Python 3 version
except AttributeError:
    yaml.SafeDumper.orig_represent_str = yaml.SafeDumper.represent_str
    def repr_str(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar(
                u'tag:yaml.org,2002:str', data, style='|')
        return dumper.orig_represent_str(data)
    yaml.add_representer(str, repr_str, Dumper=yaml.SafeDumper)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Convert
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def read_manual(plan_id, case_id, disabled, with_script):
    """
    Reads metadata of manual test cases from Nitrate
    """
    nitrate = tmt.export.import_nitrate()
    # Turns off nitrate caching
    nitrate.set_cache_level(0)

    try:
        tree = fmf.Tree(os.getcwd())
    except fmf.utils.RootError:
        raise ConvertError("Initialize metadata tree using 'tmt init'.")

    try:
        if plan_id:
            all_cases = nitrate.TestPlan(int(plan_id)).testcases
            case_ids = [case.id for case in all_cases if not case.automated]
        else:
            case_ids = [int(case_id)]
    except ValueError:
        raise ConvertError('Test plan/case identifier must be an integer.')

    # Create directory to store manual tests in
    old_cwd = os.getcwd()
    os.chdir(tree.root)
    try:
        os.mkdir('Manual')
    except FileExistsError:
        pass

    os.chdir('Manual')

    for case_id in case_ids:
        testcase = nitrate.TestCase(case_id)
        if testcase.status.name != 'CONFIRMED' and not disabled:
            log.debug(
                testcase.identifier + ' skipped (testcase is not CONFIRMED).')
            continue
        if testcase.script is not None and not with_script:
            log.debug(testcase.identifier + ' skipped (script is not empty).')
            continue

        # Filename sanitization
        dir_name = testcase.summary.replace(' ', '_')
        dir_name = dir_name.replace('/', '_')
        try:
            os.mkdir(dir_name)
        except FileExistsError:
            pass

        os.chdir(dir_name)
        echo("Importing the '{0}' test case.".format(dir_name))

        # Test case data
        md_content = read_manual_data(testcase)

        # Test case metadata
        data = read_nitrate_case(testcase)
        data['manual'] = True
        data['test'] = 'test.md'

        write_markdown(os.getcwd() + '/test.md', md_content)
        write(os.getcwd() + '/main.fmf', data)
        os.chdir('..')

    os.chdir(old_cwd)


def read_manual_data(testcase):
    """ Read test data from manual fields """
    md_content = {}
    md_content['setup'] = html_to_markdown(testcase.setup)
    md_content['action'] = html_to_markdown(testcase.action)
    md_content['expected'] = html_to_markdown(testcase.effect)
    md_content['cleanup'] = html_to_markdown(testcase.breakdown)
    return md_content


def html_to_markdown(html):
    """ Convert html to markdown """
    try:
        import html2text
        md_handler = html2text.HTML2Text()
    except ImportError:
        raise ConvertError("Install tmt-test-convert to import tests.")

    if html is None:
        markdown = ""
    else:
        markdown = md_handler.handle(html).strip()
    return markdown


def write_markdown(path, content):
    """ Write gathered metadata in the markdown format """
    to_print = ""
    if content['setup']:
        to_print += "# Setup\n" + content['setup'] + '\n\n'
    if content['action'] or content['expected']:
        to_print += "# Test\n\n"
        if content['action']:
            to_print += "## Step\n" + content['action'] + '\n\n'
        if content['expected']:
            to_print += "## Expect\n" + content['expected'] + '\n\n'
    if content['cleanup']:
        to_print += "# Cleanup\n" + content['cleanup'] + '\n'

    try:
        with open(path, 'w', encoding='utf-8') as md_file:
            md_file.write(to_print)
            echo(style(
                f"Test case successfully stored into '{path}'.", fg='magenta'))
    except IOError:
        raise ConvertError(f"Unable to write '{path}'.")


def read(path, makefile, nitrate, purpose, disabled):
    """
    Read old metadata from various sources

    Returns tuple (common_data, individual_data) where 'common_data' are
    metadata which belong to main.fmf and 'individual_data' contains
    data for individual testcases (if multiple nitrate testcases found).
    """

    data = dict(framework='beakerlib')
    echo("Checking the '{0}' directory.".format(path))

    # Make sure there is a metadata tree initialized
    try:
        tree = fmf.Tree(path)
    except fmf.utils.RootError:
        raise ConvertError("Initialize metadata tree using 'tmt init'.")

    # Makefile (extract summary, test, duration and requires)
    if makefile:
        echo(style('Makefile ', fg='blue'), nl=False)
        makefile_path = os.path.join(path, 'Makefile')
        try:
            with open(makefile_path, encoding='utf-8') as makefile_file:
                makefile = makefile_file.read()
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(makefile_path))
        echo("found in '{0}'.".format(makefile_path))

        # If testinfo.desc exists read it to preserve content and remove it
        testinfo_path = os.path.join(path, 'testinfo.desc')
        if os.path.isfile(testinfo_path):
            try:
                with open(testinfo_path, encoding='utf-8') as testinfo:
                    old_testinfo = testinfo.read()
                    os.remove(testinfo_path)
            except IOError:
                raise ConvertError(
                    "Unable to open '{0}'.".format(testinfo_path))
        else:
            old_testinfo = None

        # Make Makefile 'makeable' without extra dependecies
        # (replace targets, make include optional and remove rhts-lint)
        makefile = makefile.replace('$(METADATA)', 'testinfo.desc')
        makefile = re.sub(
                r'^include /usr/share/rhts/lib/rhts-make.include',
                '-include /usr/share/rhts/lib/rhts-make.include',
                makefile, flags=re.MULTILINE)
        makefile = re.sub('.*rhts-lint.*', '', makefile)

        # Create testinfo.desc file with resolved variables
        try:
            process = subprocess.run(
                ["make", "testinfo.desc", "-C", path, "-f", "-"],
                input=makefile, check=True, encoding='utf-8',
                stdout=subprocess.DEVNULL)
        except FileNotFoundError:
            raise ConvertError(
                "Install tmt-test-convert to convert metadata from Makefile.")
        except subprocess.CalledProcessError:
            raise ConvertError(
                "Failed to convert metadata using 'make testinfo.desc'.")

        # Read testinfo.desc
        try:
            with open(testinfo_path, encoding='utf-8') as testinfo_file:
                testinfo = testinfo_file.read()
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(testinfo_path))

        # Beaker task name
        try:
            beaker_task = re.search(r'Name:\s*(.*)\n', testinfo).group(1)
            echo(style('task: ', fg='green') + beaker_task)
            data['extra-task'] = beaker_task
            data['extra-summary'] = beaker_task
        except AttributeError:
            raise ConvertError("Unable to parse 'Name' from testinfo.desc.")
        # Summary
        try:
            data['summary'] = re.search(
                r'^Description:\s*(.*)\n', testinfo, re.M).group(1)
            echo(style('summary: ', fg='green') + data['summary'])
        except AttributeError:
            pass
        # Test script
        try:
            data['test'] = re.search(
                r'^run:.*\n\t(.*)$', makefile, re.M).group(1)
            echo(style('test: ', fg='green') + data['test'])
        except AttributeError:
            raise ConvertError("Makefile is missing the 'run' target.")
        # Contact
        try:
            data['contact'] = re.search(
                r'^Owner:\s*(.*)', testinfo, re.M).group(1)
            echo(style('contact: ', fg='green') + data['contact'])
        except AttributeError:
            pass
        # Component
        try:
            data['component'] = re.search(
                r'^RunFor:\s*(.*)', testinfo, re.M).group(1).split()
            echo(style('component: ', fg='green') +
                 ' '.join(data['component']))
        except AttributeError:
            pass
        # Duration
        try:
            data['duration'] = re.search(
                r'^TestTime:\s*(.*)', testinfo, re.M).group(1)
            echo(style('duration: ', fg='green') + data['duration'])
        except AttributeError:
            pass
        # Environment
        variables = re.findall(r'^Environment:\s*(.*)', testinfo, re.M)
        if variables:
            data['environment'] = {}
            for variable in variables:
                key, value = variable.split('=', maxsplit=1)
                data['environment'][key] = value
            echo(style('environment:', fg='green'))
            echo(pprint.pformat(data['environment']))
        # RhtsRequires (optional) goes to require
        requires = re.findall(r'^RhtsRequires:\s*(.*)', testinfo, re.M)
        if requires:
            data['require'] = [
                require for line in requires for require in line.split()]
            echo(style('require: ', fg='green') + ' '.join(data['require']))

        # Requires (optional) goes to recommend
        recommends = re.findall(r'^Requires:\s*(.*)', testinfo, re.M)
        if recommends:
            data['recommend'] = [
                recommend for line in recommends for recommend in line.split()]
            echo(
                style('recommend: ', fg='green') + ' '.join(data['recommend']))

        # Restore the original testinfo.desc content (if existed)
        if old_testinfo:
            try:
                with open(testinfo_path, 'w', encoding='utf-8') as testinfo:
                    testinfo.write(old_testinfo)
            except IOError:
                raise ConvertError(
                    "Unable to write '{0}'.".format(testinfo_path))
        # Remove created testinfo.desc otherwise
        else:
            os.remove(testinfo_path)

    # Purpose (extract everything after the header as a description)
    if purpose:
        echo(style('Purpose ', fg='blue'), nl=False)
        purpose_path = os.path.join(path, 'PURPOSE')
        try:
            with open(purpose_path, encoding='utf-8') as purpose:
                content = purpose.read()
            echo("found in '{0}'.".format(purpose_path))
            for header in ['PURPOSE', 'Description', 'Author']:
                content = re.sub('^{0}.*\n'.format(header), '', content)
            data['description'] = content.lstrip('\n')
            echo(style('description:', fg='green'))
            echo(data['description'].rstrip('\n'))
        except IOError:
            echo("not found.")

    # Nitrate (extract contact, environment and relevancy)
    if nitrate:
        common_data, individual_data = read_nitrate(
            beaker_task, data, disabled)
    else:
        common_data = data
        individual_data = []

    # Remove keys which are inherited from parent
    parent_path = os.path.dirname(path.rstrip('/'))
    parent_name = '/' + os.path.relpath(parent_path, tree.root)
    parent = tree.find(parent_name)
    if parent:
        for test in [common_data] + individual_data:
            for key in list(test):
                if parent.get(key) == test[key]:
                    test.pop(key)

    log.debug('Common metadata:\n' + pprint.pformat(common_data))
    log.debug('Individual metadata:\n' + pprint.pformat(individual_data))
    return common_data, individual_data


def read_nitrate(beaker_task, common_data, disabled):
    """ Read old metadata from nitrate test cases """

    # Need to import nitrate only when really needed. Otherwise we get
    # traceback when nitrate is not installed or config file not available.
    try:
        import nitrate
        import gssapi
    except ImportError:
        raise ConvertError('Install tmt-test-convert to import metadata.')

    # Check test case
    echo(style('Nitrate ', fg='blue'), nl=False)
    if beaker_task is None:
        raise ConvertError('No test name detected for nitrate search')

    # Find all testcases
    try:
        if disabled:
            testcases = list(nitrate.TestCase.search(script=beaker_task))
        # Find testcases that do not have 'DISABLED' status
        else:
            testcases = list(nitrate.TestCase.search(
                script=beaker_task, case_status__in=[1, 2, 4]))
    except (nitrate.NitrateError, gssapi.raw.misc.GSSError) as error:
        raise ConvertError(error)
    if not testcases:
        echo("No {0}testcase found for '{1}'.".format(
            '' if disabled else 'non-disabled ', beaker_task))
        return common_data, []
    elif len(testcases) > 1:
        echo("Multiple test cases found for '{0}'.".format(beaker_task))

    # Process individual test cases
    individual_data = list()
    md_content = dict()
    for testcase in testcases:
        # Testcase data must be fetched due to
        # https://github.com/psss/python-nitrate/issues/24
        testcase._fetch()
        data = read_nitrate_case(testcase, common_data)
        individual_data.append(data)
        # Check testcase for manual data
        md_content_tmp = read_manual_data(testcase)
        if any(md_content_tmp.values()):
            md_content = md_content_tmp

    # Write md file if there is something to write
    # or try to remove if there isn't.
    md_path = os.getcwd() + '/test.md'
    if md_content:
        write_markdown(md_path , md_content)
    else:
        try:
            os.remove(md_path)
            echo(style(f"Test case file '{md_path}' "
            "successfully removed.", fg='magenta'))
        except FileNotFoundError:
            pass
        except IOError:
            raise ConvertError(
                "Unable to remove '{0}'.".format(md_path))

    # Merge environment from Makefile and Nitrate
    if 'environment' in common_data:
        for case in individual_data:
            if 'environment' in case:
                case_environment = case['environment']
                case['environment'] = common_data['environment'].copy()
                case['environment'].update(case_environment)

    # Merge description from PURPOSE with header/footer from Nitrate notes
    for testcase in individual_data:
        if 'description' in common_data:
            testcase['description'] = common_data['description'] + \
                testcase['description']

    if 'description' in common_data:
        common_data.pop('description')

    # Find common data from individual test cases
    common_candidates = dict()
    histogram = dict()
    for testcase in individual_data:
        if individual_data.index(testcase) == 0:
            common_candidates = copy.copy(testcase)
            for key in testcase:
                histogram[key] = 1
        else:
            for key, value in testcase.items():
                if key in common_candidates:
                    if value != common_candidates[key]:
                        common_candidates.pop(key)
                if key in histogram:
                    histogram[key] += 1

    for key in histogram:
        if key in common_candidates and histogram[key] < len(individual_data):
            common_candidates.pop(key)

    # Add common data to main.fmf
    for key, value in common_candidates.items():
        common_data[key] = value

    # If there is only single testcase found there is no need to continue
    if len(individual_data) <= 1:
        return common_data, []

    # Remove common data from individual fmfs
    for common_key in common_candidates:
        for testcase in individual_data:
            if common_key in testcase:
                testcase.pop(common_key)

    return common_data, individual_data


def read_nitrate_case(testcase, makefile_data=None):
    """ Read old metadata from nitrate test case """
    data = dict()
    echo("test case found '{0}'.".format(testcase.identifier))
    # Test identifier
    data['extra-nitrate'] = testcase.identifier
    # Beaker task name (taken from summary)
    if testcase.summary:
        data['extra-summary'] = testcase.summary
        echo(style('extra-summary: ', fg='green') + data['extra-summary'])
    # Contact
    if testcase.tester:
        # Full 'Name Surname <example@email.com>' form
        if testcase.tester.name is not None:
            data['contact'] = '{} <{}>'.format(
                testcase.tester.name, testcase.tester.email)
        else:
            try:
                # Use contact from Makefile if it's there and email matches
                if re.search(testcase.tester.email, makefile_data['contact']):
                    data['contact'] = makefile_data['contact']
                else:
                    raise KeyError
            except (KeyError, TypeError):
                # Otherwise use just the email address
                data['contact'] = testcase.tester.email
        echo(style('contact: ', fg='green') + data['contact'])
    # Environment
    if testcase.arguments:
        data['environment'] = tmt.utils.shell_to_dict(testcase.arguments)
        if not data['environment']:
            data.pop('environment')
        else:
            echo(style('environment:', fg='green'))
            echo(pprint.pformat(data['environment']))
    # Tags
    if testcase.tags:
        tags = []
        for tag in testcase.tags:
            if tag.name == 'fmf-export':
                continue
            tags.append(tag.name)
            # Add the tier attribute, if there are multiple TierX tags,
            # pick the one with the lowest index.
            tier_match = re.match(r'^Tier ?(?P<num>\d+)$', tag.name, re.I)
            if tier_match:
                num = tier_match.group('num')
                if 'tier' in data:
                    log.warning('Multiple Tier tags found, using the one '
                                'with a lower index')
                    if int(num) < int(data['tier']):
                        data['tier'] = num
                else:
                    data['tier'] = num

        data['tag'] = sorted(tags)
        echo(style('tag: ', fg='green') + str(data['tag']))
    # Tier
    try:
        echo(style('tier: ', fg='green') + data['tier'])
    except KeyError:
        pass
    # Component
    data['component'] = [comp.name for comp in testcase.components]
    echo(style('component: ', fg='green') + ' '.join(data['component']))
    # Status
    data['enabled'] = testcase.status.name == "CONFIRMED"
    echo(style('enabled: ', fg='green') + str(data['enabled']))
    # Set manual attribute to manual tests only
    if not testcase.automated:
        data['manual'] = True
    # Relevancy
    field = tmt.utils.StructuredField(testcase.notes)
    try:
        relevancy = field.get('relevancy')
        if relevancy:
            data['adjust'] = relevancy_to_adjust(relevancy)
            echo(style('adjust:', fg='green'))
            echo(tmt.utils.dict_to_yaml(data['adjust']).strip())
    except tmt.utils.StructuredFieldError:
        pass

    # Header and footer from notes
    data['description'] = field.header() + field.footer()

    # Extras: [pepa] and [hardware]
    try:
        extra_pepa = field.get('pepa')
        if extra_pepa:
            data['extra-pepa'] = extra_pepa
            echo(style('extra-pepa:', fg='green'))
            echo(data['extra-pepa'].rstrip('\n'))
    except tmt.utils.StructuredFieldError:
        pass
    try:
        extra_hardware = field.get('hardware')
        if extra_hardware:
            data['extra-hardware'] = extra_hardware
            echo(style('extra-hardware:', fg='green'))
            echo(data['extra-hardware'].rstrip('\n'))
    except tmt.utils.StructuredFieldError:
        pass

    return data


def adjust_runtest(path):
    """ Adjust runtest.sh content and permission """

    # Nothing to do if there is no runtest.sh
    if not os.path.exists(path):
        return

    # Remove sourcing of rhts-environment.sh and update beakerlib path
    rhts_line = '. /usr/bin/rhts-environment.sh'
    old_beakerlib_path1 = '. /usr/lib/beakerlib/beakerlib.sh'
    old_beakerlib_path2 = '. /usr/share/rhts-library/rhtslib.sh'
    new_beakerlib_path = '. /usr/share/beakerlib/beakerlib.sh || exit 1\n'
    try:
        with open(path, 'r+') as runtest:
            lines = runtest.readlines()
            runtest.seek(0)
            for line in lines:
                if rhts_line in line:
                    echo(style(
                        "Removing sourcing of 'rhts-environment.sh' "
                        "from 'runtest.sh'.", fg='magenta'))
                elif (old_beakerlib_path1 in line
                        or old_beakerlib_path2 in line):
                    runtest.write(new_beakerlib_path)
                    echo(style(
                        "Replacing old beakerlib path with new one "
                        "in 'runtest.sh'.", fg='magenta'))
                else:
                    runtest.write(line)
            runtest.truncate()
    except IOError:
        raise ConvertError("Unable to read/write '{0}'.".format(path))

    # Make sure the script has correct execute permissions
    try:
        os.chmod(path, 0o755)
    except IOError:
        raise tmt.convert.ConvertError(
            "Could not make '{0}' executable.".format(path))


def write(path, data):
    """ Write gathered metadata in the fmf format """
    # Put keys into a reasonable order
    extra_keys = [
        'adjust', 'extra-nitrate',
        'extra-summary', 'extra-task',
        'extra-hardware', 'extra-pepa']
    sorted_data = dict()
    for key in tmt.base.Test._keys + extra_keys:
        try:
            sorted_data[key] = data[key]
        except KeyError:
            pass
    # Store metadata into a fmf file
    try:
        with open(path, 'w', encoding='utf-8') as fmf_file:
            fmf_file.write(tmt.utils.dict_to_yaml(sorted_data))
    except IOError:
        raise ConvertError("Unable to write '{0}'".format(path))
    echo(style(
        "Metadata successfully stored into '{0}'.".format(path), fg='magenta'))


def relevancy_to_adjust(relevancy):
    """
    Convert the old test case relevancy into adjust rules

    Expects a string or list of strings with relevancy rules.
    Returns a list of dictionaries with adjust rules.
    """
    rules = list()
    rule = dict()
    if isinstance(relevancy, list):
        relevancy = '\n'.join(str(line) for line in relevancy)

    for line in re.split(r'\s*\n\s*', relevancy.strip()):
        # Extract possible comments
        try:
            line, rule['because'] = re.search(RELEVANCY_COMMENT, line).groups()
        except Exception:
            pass

        # Nothing to do with empty lines
        if not line:
            continue

        # Split rule
        try:
            condition, decision = re.search(RELEVANCY_RULE, line).groups()
        except Exception:
            raise tmt.utils.ConvertError(
                f"Invalid test case relevancy rule '{line}'.")

        # Handle the decision
        if decision.lower() == 'false':
            rule['enabled'] = False
        else:
            try:
                rule['environment'] = tmt.utils.shell_to_dict(decision)
            except tmt.utils.GeneralError:
                raise tmt.utils.ConvertError(
                    f"Invalid test case relevancy decision '{decision}'.")

        # Adjust condition syntax
        expressions = list()
        for expression in re.split(r'\s*&&?\s*', condition):
            try:
                left, operator, right = re.match(
                    RELEVANCY_EXPRESSION, expression).groups()
            except Exception:
                raise tmt.utils.ConvertError(
                    f"Invalid test case relevancy expression '{expression}'.")
            # Always use double == for equality comparison
            if operator == '=':
                operator = '=='
            # Basic operators
            if operator in ['==', '!=', '<', '<=', '>', '>=']:
                # Use the special comparison for product and distro
                # when the definition specifies a minor version
                if left in ['distro', 'product'] and '.' in right:
                    operator = '~' + ('=' if operator == '==' else operator)
            # Special operators
            else:
                try:
                    operator = {
                        'contains': '==',
                        '!contains': '!=',
                        'defined': 'is defined',
                        '!defined': 'is not defined',
                        }[operator]
                except KeyError:
                    raise tmt.utils.ConvertError(
                        f"Invalid test case relevancy operator '{operator}'.")
            # Join 'left operator right' with spaces
            expressions.append(
                ' '.join([item for item in [left, operator, right] if item]))

        # Finish the rule definition
        rule['when'] = ' and '.join(expressions)
        rule['continue'] = False
        rules.append(rule)
        rule = dict()

    return rules
