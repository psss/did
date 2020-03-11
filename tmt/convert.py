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
            with open(makefile_path, encoding='utf-8') as makefile:
                makefile_content = makefile.read()
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(makefile_path))
        echo("found in '{0}'.".format(makefile_path))

        testinfo_path = os.path.join(path, 'testinfo.desc')
        # If testinfo.desc exists read it to preserve content and remove it
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

        # Changes in order to make Makefile 'makeable' without extra dependecies
        makefile_content = makefile_content.replace(
            '$(METADATA)', 'testinfo.desc')
        makefile_content = makefile_content.replace('include /usr/share/rhts/lib/rhts-make.include',
                                                    '-include /usr/share/rhts/lib/rhts-make.include')
        makefile_content = makefile_content.replace('rhts-lint testinfo.desc', '')
        # Creating testinfo.desc file which has resolved variables
        p = subprocess.run(["make", "testinfo.desc", "-C", path, "-f", "-"], input=makefile_content,
                           encoding='ascii', stdout=subprocess.DEVNULL)  # , stderr=subprocess.DEVNULL)
        if p.returncode:
            raise ConvertError(
                "Unable to 'make testinfo.desc' with '{0}'.".format(makefile_path))

        # Read testinfo.desc
        try:
            with open(testinfo_path, encoding='utf-8') as testinfo:
                testinfo_content = testinfo.read()
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(testinfo_path))

        # Beaker task name
        try:
            beaker_task = re.search(
                'Name:\s*(.*)\n', testinfo_content).group(1)
            echo(style('task: ', fg='green') + beaker_task)
            data['extra-task'] = beaker_task
        except AttributeError:
            raise ConvertError(
                "Unable to parse 'Name' from the testinfo.desc.")
        # Summary
        data['summary'] = re.search(
            r'^Description:\s*(.*)\n', testinfo_content, re.M).group(1)
        echo(style('summary: ', fg='green') + data['summary'])
        # Test script
        data['test'] = re.search(
            '^run:.*\n\t(.*)$', makefile_content, re.M).group(1)
        echo(style('test: ', fg='green') + data['test'])
        # Component
        data['component'] = re.search(
            r'^RunFor:\s*(.*)', testinfo_content, re.M).group(1).split()
        echo(style('component: ', fg='green') + ' '.join(data['component']))
        # Duration
        try:
            data['duration'] = re.search(
                r'^TestTime:\s*(.*)', testinfo_content, re.M).group(1)
            echo(style('duration: ', fg='green') + data['duration'])
        except AttributeError:
            pass
        # Requires and RhtsRequires (optional)
        requires = re.findall(
            r'^(?:Rhts)?Requires:\s*(.*)', testinfo_content, re.M)
        if requires:
            data['require'] = [
                require for line in requires for require in line.split()]
            echo(style('require: ', fg='green') + ' '.join(data['require']))

        # testinfo.desc existed before import -> replace it with original content
        if old_testinfo:
            try:
                with open(testinfo_path, mode='w', encoding='utf-8') as testinfo:
                    testinfo.write(old_testinfo)
            except IOError:
                raise ConvertError(
                    "Unable to write '{0}'.".format(testinfo_path))
        # testinfo.desc didn't exist before import -> remove it
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
                content = re.sub(
                    '^{0}.*\n'.format(header), '', content)
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

    # Check test case, make sure nitrate is available
    echo(style('Nitrate ', fg='blue'), nl=False)
    if beaker_task is None:
        raise ConvertError('No test name detected for nitrate search')
    if TestCase is None:
        raise ConvertError('Need nitrate module to import metadata')

    # Find all testcases
    if disabled:
        testcases = list(TestCase.search(script=beaker_task))
    # Find testcases that do not have 'DISABLED' status
    else:
        testcases = list(TestCase.search(
            script=beaker_task, case_status__in=[1, 2, 4]))
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
            echo(style('environment:', fg='green'))
            echo(pprint.pformat(data['environment']))
        # Tags
        if testcase.tags:
            data['tag'] = sorted([
                tag.name for tag in testcase.tags if tag.name != 'fmf-export'])
            echo(style('tag: ', fg='green') + str(data['tag']))
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
        "Metadata successfully stored into '{0}'.".format(path), fg='magenta'))
