# coding: utf-8

""" Export metadata into nitrate """

from click import echo, style

import tmt.utils
import email
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
        global nitrate, DEFAULT_PRODUCT, gssapi
        import nitrate
        import gssapi
        DEFAULT_PRODUCT = nitrate.Product(name='RHEL Tests')
        return nitrate
    except ImportError:
        raise ConvertError(
            "Install tmt-test-convert to export tests to nitrate.")
    except nitrate.NitrateError as error:
        raise ConvertError(error)


def export_to_nitrate(test, create, general):
    """ Export fmf metadata to nitrate test cases """
    import_nitrate()

    new_test_created = False
    # Check nitrate test case
    try:
        nitrate_id = test.node.get('extra-nitrate')[3:]
        nitrate_case = nitrate.TestCase(int(nitrate_id))
        nitrate_case.summary # Make sure we connect to the server now
        echo(style(f"Test case '{nitrate_case.identifier}' found.", fg='blue'))
    except TypeError:
        # Create a new nitrate test case
        if create:
            nitrate_case = create_nitrate_case(test)
            new_test_created = True
        else:
            raise ConvertError("Nitrate test case id not found.")
    except (nitrate.NitrateError, gssapi.raw.misc.GSSError) as error:
        raise ConvertError(error)

    # Summary
    summary = test.node.get(
        'extra-summary', test.node.get('extra-task', test.summary))
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
        echo(style('components: ', fg='green') + ' '.join(test.component))
        for component in test.component:
            try:
                nitrate_case.components.add(nitrate.Component(
                    name=component, product=DEFAULT_PRODUCT.id))
            except nitrate.xmlrpc_driver.NitrateError as error:
                log.debug(error)
                echo(style(
                    f"Failed to add component '{component}'.", fg='red'))
            if general:
                try:
                    general_plan = find_general_plan(component)
                    nitrate_case.testplans.add(general_plan)
                except nitrate.NitrateError as error:
                    log.debug(error)
                    echo(style(
                        f"Failed to link general test plan for '{component}'.",
                        fg='red'))

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
        # Need to pick one value, so picking the first contact
        email_address = email.utils.parseaddr(test.contact[0])[1]
        # TODO handle nitrate user not existing and other possible exceptions
        nitrate_case.tester = nitrate.User(email_address)
        echo(style('default tester: ', fg='green') + email_address)

    # Duration
    nitrate_case.time = test.duration
    echo(style('estimated time: ', fg='green') + test.duration)

    # Manual
    nitrate_case.automated = not test.manual
    echo(style('automated: ', fg='green') + ['auto', 'manual'][test.manual])

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
    fmf_id = tmt.utils.dict_to_yaml(test.fmf_id)
    struct_field.set('fmf', fmf_id)
    echo(style('fmf id:\n', fg='green') + fmf_id.strip())

    # Warning
    if WARNING not in struct_field.header():
        struct_field.header(WARNING + struct_field.header())
        echo(style(
            'Add migration warning to the test case notes.', fg='green'))

    # Saving case.notes with edited StructField
    nitrate_case.notes = struct_field.save()

    # Append id of newly created nitrate case to its file
    if new_test_created:
        fmf_file_path = test.node.sources[-1]
        echo(style(f"Append test case id into '{fmf_file_path}'.", fg='green'))
        try:
            with open(fmf_file_path, encoding='utf-8', mode='a+') as fmf_file:
                fmf_file.write(f"extra-nitrate: {nitrate_case.identifier}\n")
        except IOError:
            raise ConvertError("Unable to open '{0}'.".format(fmf_file_path))

    # Update nitrate test case
    nitrate_case.update()
    echo(style("Test case '{0}' successfully exported to nitrate.".format(
        nitrate_case.identifier), fg='magenta'))


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


def find_general_plan(component):
    """ Return single General Test Plan or raise an error """
    # At first find by linked components
    found = nitrate.TestPlan.search(
        type__name="General",
        is_active=True,
        component__name=f"{component}")
    # Attempt to find by name if no test plan found
    if not found:
        found = nitrate.TestPlan.search(
            type__name="General",
            is_active=True,
            name=f"{component} / General")
    # No general -> raise error
    if not found:
        raise nitrate.NitrateError(
            f"No general test plan found for '{component}'.")
    # Multiple general plans are fishy -> raise error
    if len(found) != 1:
        nitrate.NitrateError(
            "Multiple general test plans found for '{component}' component.")
    # Finally return the one and only General plan
    return found[0]
