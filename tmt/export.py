# coding: utf-8

""" Export metadata into nitrate """

from click import echo, style

import subprocess
import tmt.utils
import email
import yaml
import fmf
import os

log = fmf.utils.Logging('tmt').logger

WARNING = """
Test case has been migrated to git. Any changes made here might be overwritten.
See: https://tmt.readthedocs.io/en/latest/questions.html#nitrate-migration
""".lstrip()


def export_to_nitrate(test):
    """ Export fmf metadata to nitrate test cases """
    # Need to import nitrate only when really needed. Otherwise we get
    # traceback when nitrate not installed or config file not available.
    try:
        import nitrate
        DEFAULT_PRODUCT = nitrate.Product(name='RHEL Tests')
    except ImportError:
        raise tmt.utils.ConvertError("Install nitrate to export tests there.")
    except nitrate.NitrateError as error:
        raise tmt.utils.ConvertError(error)

    # Check nitrate test case
    try:
        nitrate_id = test.node.get('extra-nitrate')[3:]
    except KeyError:
        return 0
    nitrate_case = nitrate.TestCase(int(nitrate_id))
    echo(style(f"Test case '{nitrate_case.identifier}' found.", fg='blue'))

    # Components
    # First remove any components that are already there
    nitrate_case.components.clear()
    # Then add fmf ones
    if test.component:
        components = [
            nitrate.Component(name=component, product=DEFAULT_PRODUCT.id)
            for component in test.component]
        # TODO exception not existing component
        nitrate_case.components.add(components)
        echo(style('components: ', fg='green') + ' '.join(test.component))

    # Tags
    nitrate_case.tags.clear()
    # Convert 'tier' attribute into a Tier tag
    if test.tier is not None:
        test.tag.append(f"Tier{test.tier}")
    # Add special fmf-export tag
    test.tag.append('fmf-export')
    nitrate_case.tags.add([nitrate.Tag(tag) for tag in test.tag])
    echo(style('tags: ', fg='green') + ' '.join(set(test.tag)))

    # Default tester
    if test.contact:
        email_address = email.utils.parseaddr(test.contact)[1]
        # TODO handle nitrate user not existing and other possible exceptions
        nitrate_case.tester = nitrate.User(email_address)
        echo(style('default tester: ', fg='green') + email_address)

    # Duration
    nitrate_case.time = test.duration
    echo(style('estimated time: ', fg='green') + test.duration)

    # Status
    current_status = nitrate_case.status
    # Enable enabled tests
    if test.enabled:
        nitrate_case.status = nitrate.CaseStatus('CONFIRMED')
        echo(style('status: ', fg='green') + 'CONFIRMED')
    # Disable disabled tests which are CONFIRMED
    elif current_status == nitrate.CaseStatus('CONFIRMED'):
        nitrate_case.status = nitrate.CaseStatus('DISABLED')
        echo(style('status: ', fg='green') + 'DISABLED')
    # Keep disabled tests in their states
    else:
        echo(style('status: ', fg='green') + str(current_status))

    # Environment
    if test.environment:
        environment = ' '.join(tmt.utils.shell_variables(test.environment))
        nitrate_case.arguments = environment
        echo(style('arguments: ', fg='green') + environment)
    else:
        # FIXME unable clear to set empty arguments
        # (possibly error in xmlrpc, BZ#1805687)
        nitrate_case.arguments = ' '
        echo(style('arguments: ', fg='green') + "' '")

    # Structured Field
    struct_field = tmt.utils.StructuredField(nitrate_case.notes)
    echo(style('Structured Field: ', fg='green'))

    # Mapping of structured field sections to fmf case attributes
    section_to_attr = {
        'relevancy': test.relevancy,
        'description': test.summary,
        'purpose-file': test.description,
        'hardware': test.node.get('extra-hardware'),
        'pepa': test.node.get('extra-pepa'),
        }
    for section, attribute in section_to_attr.items():
        if attribute is None:
            try:
                struct_field.remove(section)
            except tmt.utils.StructuredFieldError:
                pass
        else:
            struct_field.set(section, attribute)
            echo(style(section + ': ', fg='green') + attribute.strip())

    # fmf identifer
    fmf_id = create_fmf_id(test)
    struct_field.set('fmf', yaml.dump(fmf_id))
    echo(style('fmf id:\n', fg='green') + yaml.dump(fmf_id).strip())

    # Warning
    if WARNING not in struct_field.header():
        struct_field.header(WARNING + struct_field.header())
        echo(style('Added warning about porting to case notes.', fg='green'))

    # Saving case.notes with edited StructField
    nitrate_case.notes = struct_field.save()

    # Update nitrate test case
    nitrate_case.update()
    echo(style("Test case '{0}' successfully exported to nitrate.".format(
        nitrate_case.identifier), fg='magenta'))

    return 0


def create_fmf_id(test):
    """ Create fmf identifier for test case """

    def run(command):
        """ Run command, return output """
        result = subprocess.run(command.split(), capture_output=True)
        return result.stdout.strip().decode("utf-8")

    fmf_id = {'name': test.name}

    # Prepare url and ref
    origin = run('git config --get remote.origin.url')
    if origin.startswith('ssh://'):
        fmf_id['url'] = 'git://' + origin.split('@')[-1]
    else:
        fmf_id['url'] = origin
    ref = run('git rev-parse --abbrev-ref HEAD')
    if ref != 'master':
        fmf_id['ref'] = ref

    # Construct path (if different from git root)
    git_root = run('git rev-parse --show-toplevel')
    fmf_root = test.node.root
    if git_root != fmf_root:
        fmf_id['path'] = os.path.join('/', os.path.relpath(fmf_root, git_root))

    return fmf_id
