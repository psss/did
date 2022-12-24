import dataclasses
import os
import types
from typing import Any, Optional, cast, overload

import tmt
import tmt.base
import tmt.options
import tmt.result
import tmt.steps
import tmt.steps.report
from tmt.utils import field

DEFAULT_NAME = "junit.xml"

junit_xml: Optional[types.ModuleType] = None

# Thanks to import burried in a function, we don't get the regular missing annotations
# but "name ... is not defined". Define a special type to follow the test suite instance
# around, and if junit_xml ever gets annotations, we can replace it with provided type.
JunitTestSuite = Any


def import_junit_xml() -> None:
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


@overload
def duration_to_seconds(duration: str) -> int: pass


@overload
def duration_to_seconds(duration: None) -> None: pass


def duration_to_seconds(duration: Optional[str]) -> Optional[int]:
    """ Convert valid duration string in to seconds """
    if duration is None:
        return None
    try:
        h, m, s = duration.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception as error:
        raise tmt.utils.ReportError(
            f"Malformed duration '{duration}' ({error}).")


def make_junit_xml(report: "tmt.steps.report.ReportPlugin") -> JunitTestSuite:
    """ Create junit xml object """
    import_junit_xml()
    assert junit_xml

    suite = junit_xml.TestSuite(report.step.plan.name)

    for result in report.step.plan.execute.results():
        try:
            main_log = report.step.plan.execute.read(result.log[0])
        except (IndexError, AttributeError):
            main_log = None
        case = junit_xml.TestCase(
            result.name,
            classname=None,
            elapsed_sec=duration_to_seconds(result.duration),
            stdout=main_log)
        # Map tmt OUTCOME to JUnit states
        if result.result == tmt.result.ResultOutcome.ERROR:
            case.add_error_info(result.result.value, output=result.failures(main_log))
        elif result.result == tmt.result.ResultOutcome.FAIL:
            case.add_failure_info(result.result.value, output=result.failures(main_log))
        elif result.result == tmt.result.ResultOutcome.INFO:
            case.add_skipped_info(result.result.value, output=result.failures(main_log))
        elif result.result == tmt.result.ResultOutcome.WARN:
            case.add_error_info(result.result.value, output=result.failures(main_log))
        # Passed state is the default
        suite.test_cases.append(case)

    return cast(JunitTestSuite, suite)


@dataclasses.dataclass
class ReportJUnitData(tmt.steps.report.ReportStepData):
    file: Optional[str] = field(
        default=None,
        option='--file',
        metavar='FILE',
        help='Path to the file to store junit to.'
        )


@tmt.steps.provides_method('junit')
class ReportJUnit(tmt.steps.report.ReportPlugin):
    """
    Write test results in JUnit format

    When FILE is not specified output is written to the 'junit.xml'
    located in the current workdir.
    """

    _data_class = ReportJUnitData

    def prune(self) -> None:
        """ Do not prune generated junit report """
        pass

    def go(self) -> None:
        """ Read executed tests and write junit """
        super().go()

        suite = make_junit_xml(self)

        assert junit_xml  # narrow type

        assert self.workdir is not None
        f_path = self.get("file", os.path.join(self.workdir, DEFAULT_NAME))
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
