# coding: utf-8

""" Convert metadata into the new format """

from io import open
from click import echo, style
from tmt.utils import ConvertError, StructuredFieldError

import fmf.utils
import tmt.utils
import pprint
import copy
import yaml
import re
import os

log = fmf.utils.Logging('tmt').logger

# Import nitrate conditionally (reading from nitrate can be skipped)
try:
    from nitrate import TestCase
except ImportError:
    TestCase = None

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

def read(path, makefile, nitrate, purpose):
    """
    Read old metadata from various sources

    Returns tuple (common_data, individual_data) where 'common_data' are
    metadata which belong to main.fmf and 'individual_data' contains
    data for individual testcases (if multiple tcms testcases found).
    """

    data = dict()
    echo(style("Checking the '{0}' directory.".format(path), fg='red'))

    # Makefile (extract summary, component, duration and requires)
    if makefile:
        echo(style('Makefile ', fg='blue'), nl=False)
        makefile_path = os.path.join(path, 'Makefile')
        try:
            with open(makefile_path, encoding='utf-8') as makefile:
                content = makefile.read()
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(makefile_path))
        echo("found in '{0}'.".format(makefile_path))
        # Beaker task name
        beaker_task = re.search('export TEST=(.*)\n', content).group(1)
        echo(style('test: ', fg='green') + beaker_task)
        # Summary
        data['summary'] = re.search(
            r'echo "Description:\s*(.*)"', content).group(1)
        echo(style('description: ', fg='green') + data['summary'])
        # Component
        data['component'] = re.search(
            r'echo "RunFor:\s*(.*)"', content).group(1)
        echo(style('component: ', fg='green') + data['component'])
        # Duration
        data['duration'] = re.search(
            r'echo "TestTime:\s*(.*)"', content).group(1)
        echo(style('duration: ', fg='green') + data['duration'])
        # Requires and RhtsRequires (optional)
        requires = re.findall(r'echo "(?:Rhts)?Requires:\s*(.*)"', content)
        if requires:
            data['requires'] = requires
            echo(style('requires: ', fg='green') + ' '.join(data['requires']))

    # Purpose (extract everything after the header as a description)
    if purpose:
        echo(style('Purpose ', fg='blue'), nl=False)
        purpose_path = os.path.join(path, 'PURPOSE')
        try:
            with open(purpose_path, encoding='utf-8') as purpose:
                content = purpose.read()
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(purpose_path))
        echo("found in '{0}'.".format(purpose_path))
        for header in ['PURPOSE', 'Description', 'Author']:
            content = re.sub('^{0}.*\n'.format(header), '', content)
        data['description'] = content.lstrip('\n')
        echo(style('description:', fg='green'))
        echo(data['description'].rstrip('\n'))

    # Nitrate (extract contact, environment and relevancy)
    if nitrate:
        common_data, individual_data = read_nitrate(beaker_task, data)
    else:
        common_data = data
        individual_data = []

    log.debug('Common metadata:\n' + pprint.pformat(common_data))
    log.debug('Individual metadata:\n' + pprint.pformat(individual_data))
    return common_data, individual_data


def read_nitrate(beaker_task, common_data):
    """ Read old metadata from nitrate test cases """

    # Check test case, make sure nitrate is available
    echo(style('Nitrate ', fg='blue'), nl=False)
    if beaker_task is None:
        raise ConvertError('No test name detected for nitrate search')
    if TestCase is None:
        raise ConvertError('Need nitrate module to import metadata')

    # Find testcases that have CONFIRMED status
    testcases = list(TestCase.search(script=beaker_task, case_status=2))
    if not testcases:
        raise ConvertError("No testcase found for '{0}'.".format(beaker_task))
    elif len(testcases) > 1:
        echo("Multiple test cases found for '{0}'.".format(beaker_task))

    # Process individual test cases
    individual_data = list()
    for testcase in testcases:
        data = dict()
        echo("test case found '{0}'.".format(testcase.identifier))
        # Test identifier
        data['tcms'] = testcase.identifier
        # Beaker task name (taken from summary)
        if testcase.summary:
            data['task'] = testcase.summary
            echo(style('task: ', fg='green') + data['task'])
        # Contact
        if testcase.tester:
            data['contact'] = '{} <{}>'.format(
                testcase.tester.name, testcase.tester.email)
            echo(style('contact: ', fg='green') + data['contact'])
        # Environment
        if testcase.arguments:
            data['environment'] = tmt.utils.variables_to_dictionary(
                testcase.arguments)
            echo(style('environment:', fg='green'))
            echo(pprint.pformat(data['environment']))
        # Relevancy
        field = tmt.utils.StructuredField(testcase.notes)
        relevancy = field.get('relevancy')
        if relevancy:
            data['relevancy'] = relevancy
            echo(style('relevancy:', fg='green'))
            echo(data['relevancy'].rstrip('\n'))
        individual_data.append(data)

    # Find common data from individual test cases
    common_candidates = dict()
    for testcase in individual_data:
        if individual_data.index(testcase) == 0:
            common_candidates = copy.copy(testcase)
        else:
            for key, value in testcase.items():
                if key in common_candidates:
                    if value != common_candidates[key]:
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
    # Make sure there is a metadata tree initialized
    try:
        tree = fmf.Tree(os.path.dirname(path))
    except fmf.utils.RootError:
        raise ConvertError("Initialize metadata tree using 'fmf init'.")
    # Store metadata into a fmf file
    try:
        with open(path, 'w', encoding='utf-8') as fmf_file:
            yaml.safe_dump(
                    data, fmf_file,
                    encoding='utf-8', allow_unicode=True,
                    indent=4, default_flow_style=False)
    except IOError:
        raise ConvertError("Unable to write '{0}'".format(path))
    echo(style(
        "Metadata successfully stored into '{0}'.".format(path), fg='red'))
