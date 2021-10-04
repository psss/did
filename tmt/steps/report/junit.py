import os

import click

import tmt

DEFAULT_NAME = "junit.xml"


def import_junit_xml():
    """
    Import junit_xml module only when needed

    Until we have a separate package for each plugin.
    """
    global junit_xml
    try:
        import junit_xml
    except ImportError:
        raise tmt.utils.ReportError(
            "Missing 'junit-xml', fixable by 'pip install tmt[report-junit]'.")


def duration_to_seconds(duration):
    """ Convert valid duration string in to seconds """
    if duration is None:
        return None
    try:
        h, m, s = duration.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception as error:
        raise tmt.utils.ReportError(
            f"Malformed duration '{duration}' ({error}).")


class ReportJUnit(tmt.steps.report.ReportPlugin):
    """
    Write test results in JUnit format

    When FILE is not specified output is written to the 'junit.xml'
    located in the current workdir.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='junit', doc=__doc__, order=50)]

    # Supported keys
    _keys = ["file"]

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options for connect """
        return [
            click.option(
                '--file', metavar='FILE',
                help='Path to the file to store junit to'),
            ] + super().options(how)

    def go(self):
        """ Read executed tests and write junit """
        super().go()

        import_junit_xml()

        suite = junit_xml.TestSuite(self.step.plan.name)
        for result in self.step.plan.execute.results():
            try:
                main_log = self.step.plan.execute.read(result.log[0])
            except (IndexError, AttributeError):
                main_log = None
            case = junit_xml.TestCase(
                result.name,
                classname=None,
                elapsed_sec=duration_to_seconds(result.duration),
                stdout=main_log
                )
            # Map tmt OUTCOME to JUnit states
            if result.result == "error":
                case.add_error_info(result.result)
            elif result.result == "fail":
                case.add_failure_info(result.result)
            elif result.result == "info":
                case.add_skipped_info(result.result)
            elif result.result == "warn":
                case.add_error_info(result.result)
            # Passed state is the default
            suite.test_cases.append(case)
        f_path = self.opt("file", os.path.join(self.workdir, DEFAULT_NAME))
        try:
            with open(f_path, 'w') as fw:
                if hasattr(junit_xml, 'to_xml_report_file'):
                    junit_xml.to_xml_report_file(fw, [suite])
                else:
                    # For older junit-xml
                    junit_xml.TestSuite.to_file(fw, [suite])
            self.info("output", f_path, 'yellow')
        except Exception as error:
            raise tmt.utils.ReportError(
                f"Failed to write the output '{f_path}' ({error}).")
