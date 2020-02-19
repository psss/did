# coding: utf-8

""" Export metadata into nitrate """

from click import echo, style

import subprocess
import tmt.utils
import email
import yaml
import fmf
import os

# Import nitrate conditionally
try:
    import nitrate
    # Needed for nitrate.Component
    DEFAULT_PRODUCT = nitrate.Product(name='RHEL Tests')
except ImportError:
    nitrate = None
    DEFAULT_PRODUCT = ''

log = fmf.utils.Logging('tmt').logger

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Export
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def export_to_nitrate(fmf_case):
    """ Export fmf metadata to nitrate test cases """
    fmf_case_attrs = fmf_case.node.get()
    try:
        case_id = fmf_case_attrs['extra-nitrate'][3:]
    except KeyError:
        return 0
    nitrate_case = nitrate.TestCase(int(case_id))
    echo(style("Test case '{0}' found.".format(
        fmf_case_attrs['extra-nitrate']), fg='blue'))

    # Components
    try:
        # First remove any components that are already there
        nitrate_case.components.clear()
        # Then add fmf ones
        if fmf_case_attrs['component']:
            comp_list = [nitrate.Component(
                name=comp, product=DEFAULT_PRODUCT.id) for comp in fmf_case_attrs['component']]
            # TODO exception not existing component
            nitrate_case.components.add(comp_list)
            echo(style('components: ', fg='green') +
                 ' '.join(fmf_case_attrs['component']))
    except KeyError:
        # Defaults to no components
        pass

    if 'tag' not in fmf_case_attrs:
        fmf_case_attrs['tag'] = list()

    # 'tier' attribute into Tier tag
    try:
        fmf_case_attrs['tag'].append("Tier" + str(fmf_case_attrs['tier']))
    except KeyError:
        pass

    # Tags
    nitrate_case.tags.clear()
    # Add special fmf-export tag
    fmf_case_attrs['tag'].append('fmf-export')
    tag_list = [nitrate.Tag(tag) for tag in fmf_case_attrs['tag']]
    nitrate_case.tags.add(tag_list)
    echo(style('tags: ', fg='green') +
         ' '.join(set(fmf_case_attrs['tag'])))

    # Default tester
    try:
        email_address = email.utils.parseaddr(fmf_case_attrs['contact'])[1]
        # TODO handle nitrate user not existing and other possible exceptions
        nitrate_case.tester = nitrate.User(email_address)
        echo(style('default tester: ', fg='green') + email_address)
    except KeyError:
        # Defaults to author of the test case
        pass

    # Duration
    try:
        nitrate_case.time = fmf_case_attrs['duration']
        echo(style('estimated time: ', fg='green') +
             fmf_case_attrs['duration'])
    except KeyError:
        # Defaults to 5 minutes
        nitrate_case.time = '5m'
        echo(style('estimated time: ', fg='green') + '5m')

    # Status
    current_status = nitrate_case.status
    try:
        # Enable enabled tests
        if fmf_case_attrs['enabled']:
            nitrate_case.status = nitrate.CaseStatus('CONFIRMED')
            echo(style('status: ', fg='green') + 'CONFIRMED')
        # Disable disabled tests which are CONFIRMED
        elif current_status == nitrate.CaseStatus('CONFIRMED'):
            nitrate_case.status = nitrate.CaseStatus('DISABLED')
            echo(style('status: ', fg='green') + 'DISABLED')
        # Keep disabled tests in their states
        else:
            echo(style('status: ', fg='green') + str(current_status))
    except KeyError:
        # Defaults to enabled
        nitrate_case.status = nitrate.CaseStatus('CONFIRMED')
        echo(style('status: ', fg='green') + 'CONFIRMED')

    # Environment
    try:
        env = ' '.join(tmt.utils.dict_to_shell(
            fmf_case_attrs['environment']))
        nitrate_case.arguments = env
        echo(style('arguments: ', fg='green') + env)
    except KeyError:
        # FIXME unable to set empty arguments, possibly error in xmlrpc, BZ#1805687
        nitrate_case.arguments = ' '
        echo(style('arguments: ', fg='green') + "' '")

    struct_field = tmt.utils.StructuredField(nitrate_case.notes)
    echo(style('Structured Field: ', fg='green'))

    # Mapping of structured field sections to fmf case attributes
    section_to_attr = {'relevancy': 'relevancy', 'description': 'summary',
                       'purpose-file': 'description', 'hardware': 'extra-hardware', 'pepa': 'extra-pepa'}

    for section, attribute in section_to_attr.items():
        try:
            struct_field.set(section, fmf_case_attrs[attribute])
            echo(style(section + ': ', fg='green') +
                 fmf_case_attrs[attribute].strip())
        except KeyError:
            pass

    # fmf identifer
    fmf_id = create_fmf_id(name=fmf_case.name)

    struct_field.set('fmf', yaml.dump(fmf_id))
    echo(style('fmf id:\n', fg='green') + yaml.dump(fmf_id))

    fmf_warning = """Test case was ported to fmf and is maintaned in git.
Any changes made here might be overwritten.
More information here: https://tmt.readthedocs.io/en/latest/questions.html#nitrate-migration\n\n"""
    if fmf_warning not in struct_field.header():
        struct_field.header(fmf_warning + struct_field.header())
        echo(style('Added warning about porting to case notes.', fg='green'))

    # Saving case.notes with edited StructField
    nitrate_case.notes = struct_field.save()

    # Update nitrate test case
    nitrate_case.update()
    echo(style("Test case '{0}' successfully exported to nitrate.\n".format(
        fmf_case_attrs['extra-nitrate']), fg='green'))

    return 0


def create_fmf_id(name=''):
    """ Create fmf identifier for test case """

    origin = subprocess.run(["git", "config", "--get", "remote.origin.url"],
                            capture_output=True).stdout.strip().decode("utf-8")
    if origin.startswith('ssh://'):
        url = 'git://' + origin.split('@')[-1]
    else:
        url = origin

    ref = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                         capture_output=True).stdout.strip().decode("utf-8")

    git_root = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                              capture_output=True).stdout.strip().decode("utf-8")

    fmf_root = fmf.Tree(os.path.abspath('.')).root

    if git_root == fmf_root:
        path = '.'
    else:
        path = fmf_root[len(git_root):]

    fmf_id = {'url': url, 'ref': ref, 'path': path, 'name': name}

    return fmf_id
