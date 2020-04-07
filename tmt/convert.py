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

def read(path, makefile, nitrate, purpose, disabled):
    """
    Read old metadata from various sources

    Returns tuple (common_data, individual_data) where 'common_data' are
    metadata which belong to main.fmf and 'individual_data' contains
    data for individual testcases (if multiple nitrate testcases found).
    """

    data = dict()
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
        makefile = makefile.replace(
            'include /usr/share/rhts/lib/rhts-make.include',
            '-include /usr/share/rhts/lib/rhts-make.include')
        makefile = makefile.replace('rhts-lint testinfo.desc', '')

        # Create testinfo.desc file with resolved variables
        try:
            process = subprocess.run(
                ["make", "testinfo.desc", "-C", path, "-f", "-"],
                input=makefile, check=True, encoding='utf-8',
                stdout=subprocess.DEVNULL)
        except FileNotFoundError:
            raise ConvertError(
                "Install 'make' to convert metadata from Makefile.")
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
        # Requires and RhtsRequires (optional)
        requires = re.findall(r'^(?:Rhts)?Requires:\s*(.*)', testinfo, re.M)
        if requires:
            data['require'] = [
                require for line in requires for require in line.split()]
            echo(style('require: ', fg='green') + ' '.join(data['require']))

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

    log.debug('Common metadata:\n' + pprint.pformat(common_data))
    log.debug('Individual metadata:\n' + pprint.pformat(individual_data))
    return common_data, individual_data


def read_nitrate(beaker_task, common_data, disabled):
    """ Read old metadata from nitrate test cases """

    # Need to import nitrate only when really needed. Otherwise we get
    # traceback when nitrate not installed or config file not available.
    try:
        import nitrate
    except ImportError:
        raise ConvertError('Install nitrate module to import metadata.')

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
    except nitrate.NitrateError as error:
        raise ConvertError(error)
    if not testcases:
        echo("No {0}testcase found for '{1}'.".format(
            '' if disabled else 'non-disabled ', beaker_task))
        return common_data, []
    elif len(testcases) > 1:
        echo("Multiple test cases found for '{0}'.".format(beaker_task))

    # Process individual test cases
    individual_data = list()
    for testcase in testcases:
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
            data['contact'] = '{} <{}>'.format(
                testcase.tester.name, testcase.tester.email)
            echo(style('contact: ', fg='green') + data['contact'])
        # Environment
        if testcase.arguments:
            data['environment'] = tmt.utils.variables_to_dictionary(
                testcase.arguments)
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
        # Relevancy
        field = tmt.utils.StructuredField(testcase.notes)
        try:
            relevancy = field.get('relevancy')
            if relevancy:
                data['relevancy'] = relevancy
                echo(style('relevancy:', fg='green'))
                echo(data['relevancy'].rstrip('\n'))
        except tmt.utils.StructuredFieldError:
            pass
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
        individual_data.append(data)

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


def write(path, data):
    """ Write gathered metadata in the fmf format """
    # Put keys into a reasonable order
    extra_keys = ['extra-summary', 'extra-task', 'extra-nitrate']
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
