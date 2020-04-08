# coding: utf-8

""" Export metadata into nitrate """

from click import echo, style

import tmt.utils
import email
import yaml
import fmf
import re

from tmt.utils import ConvertError

log = fmf.utils.Logging('tmt').logger

WARNING = """
Test case has been migrated to git. Any changes made here might be overwritten.
See: https://tmt.readthedocs.io/en/latest/questions.html#nitrate-migration
""".lstrip()


def import_nitrate():
    """ Conditionally import the nitrate module """
    # Need to import nitrate only when really needed. Otherwise we get
    # traceback when nitrate not installed or config file not available.
    # And we want to keep the core tmt package with minimal dependencies.
    try:
        global nitrate, DEFAULT_PRODUCT
        import nitrate
        DEFAULT_PRODUCT = nitrate.Product(name='RHEL Tests')
    except ImportError:
        raise ConvertError("Install nitrate to export tests there.")
    except nitrate.NitrateError as error:
        raise ConvertError(error)


def export_to_nitrate(test, create):
    """ Export fmf metadata to nitrate test cases """
    import_nitrate()

    new_test_created = False
    # Check nitrate test case
    try:
        nitrate_id = test.node.get('extra-nitrate')[3:]
        nitrate_case = nitrate.TestCase(int(nitrate_id))
        echo(style(f"Test case '{nitrate_case.identifier}' found.", fg='blue'))
    except TypeError:
        # Create a new nitrate test case
        if create:
            nitrate_case = create_nitrate_case(test)
            new_test_created = True
        else:
            raise ConvertError("Nitrate test case id not found.")

    # Summary
    summary = test.node.get('extra-summary', test.summary)
    if summary:
        nitrate_case.summary = summary
        echo(style('summary: ', fg='green') + summary)
    else:
        raise ConvertError("Nitrate case summary could not be determined.")

    # Script
    if test.node.get('extra-task'):
        nitrate_case.script = test.node.get('extra-task')
        echo(style('script: ', fg='green') + test.node.get('extra-task'))

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
    fmf_id = test.fmf_id
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

    # Write id of newly created nitrate case to its file
    if new_test_created:
        fmf_file_path = test.node.sources[-1]
        try:
            with open(fmf_file_path, encoding='utf-8') as fmf_file:
                content = yaml.safe_load(fmf_file)
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(fmf_file_path))

        content['extra-nitrate'] = nitrate_case.identifier
        tmt.convert.write(fmf_file_path, content)


def create_nitrate_case(test):
    """ Create new nitrate case """
    import_nitrate()

    # Get category from Makefile
    try:
        with open('Makefile', encoding='utf-8') as makefile_file:
            makefile = makefile_file.read()
        category = re.search(
            r'echo\s+"Type:\s*(.*)"', makefile, re.M).group(1)
    # Default to 'Sanity' if Makefile or Type not found
    except (IOError, AttributeError):
        category = 'Sanity'

    # Create the new test case
    summary = test.node.get('extra-summary', test.summary)
    category = nitrate.Category(name=category, product=DEFAULT_PRODUCT)
    testcase = nitrate.TestCase(summary=summary, category=category)
    echo(style(f"Test case '{testcase.identifier}' created.", fg='blue'))
    return testcase
