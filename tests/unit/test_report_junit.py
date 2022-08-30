from unittest.mock import MagicMock, PropertyMock

import pytest

from tmt import Result
from tmt.steps.report.junit import ReportJUnit


@pytest.fixture
def report_fix(tmpdir):
    # need to provide genuine workdir paths - mock would break os.path.* calls
    step_mock = MagicMock(workdir=str(tmpdir))
    plan_mock = MagicMock()
    name_property = PropertyMock(return_value='name')

    type(plan_mock).name = name_property
    type(step_mock).plan = plan_mock

    out_file_path = str(tmpdir.join("out.xml"))

    def get(key, default=None):
        if key == "file":
            return out_file_path
        return default

    report = ReportJUnit(
        step=step_mock, data={
            'name': 'x'}, workdir=str(
            tmpdir.join('junit')))
    report.get = get
    report.info = MagicMock()

    results = []

    execute_mock = MagicMock()
    type(execute_mock).results = MagicMock(return_value=results)
    type(plan_mock).execute = execute_mock

    return report, results, out_file_path


def do_assert(out_file_path, expected):
    with open(out_file_path) as f:
        output = f.read().replace('\t', ' ' * 4)
    assert output == expected


@pytest.mark.skipif(pytest.__version__.startswith('3'),
                    reason="too old pytest")
class TestStateMapping:
    def test_pass(self, report_fix):
        report, results, out_file_path = report_fix
        results.extend(
            [
                Result({
                    'result': 'pass',
                    }, "/pass")
                ]
            )

        report.go()

        do_assert(out_file_path, """<?xml version="1.0" ?>
<testsuites disabled="0" errors="0" failures="0" tests="1" time="0.0">
    <testsuite disabled="0" errors="0" failures="0" name="name" skipped="0" tests="1" time="0">
        <testcase name="/pass"/>
    </testsuite>
</testsuites>
""")

    def test_info(self, report_fix):
        report, results, out_file_path = report_fix
        results.extend(
            [
                Result({
                    'result': 'info',
                    }, "/info")
                ]
            )
        report.go()

        do_assert(out_file_path, """<?xml version="1.0" ?>
<testsuites disabled="0" errors="0" failures="0" tests="1" time="0.0">
    <testsuite disabled="0" errors="0" failures="0" name="name" skipped="1" tests="1" time="0">
        <testcase name="/info">
            <skipped type="skipped" message="info"/>
        </testcase>
    </testsuite>
</testsuites>
""")

    def test_warn(self, report_fix):
        report, results, out_file_path = report_fix
        results.extend(
            [
                Result({
                    'result': 'warn',
                    }, "/warn")
                ]
            )
        report.go()

        do_assert(out_file_path, """<?xml version="1.0" ?>
<testsuites disabled="0" errors="1" failures="0" tests="1" time="0.0">
    <testsuite disabled="0" errors="1" failures="0" name="name" skipped="0" tests="1" time="0">
        <testcase name="/warn">
            <error type="error" message="warn"/>
        </testcase>
    </testsuite>
</testsuites>
""")

    def test_error(self, report_fix):
        report, results, out_file_path = report_fix
        results.extend(
            [
                Result({
                    'result': 'error',
                    }, "/error")
                ]
            )
        report.go()

        do_assert(out_file_path, """<?xml version="1.0" ?>
<testsuites disabled="0" errors="1" failures="0" tests="1" time="0.0">
    <testsuite disabled="0" errors="1" failures="0" name="name" skipped="0" tests="1" time="0">
        <testcase name="/error">
            <error type="error" message="error"/>
        </testcase>
    </testsuite>
</testsuites>
""")

    def test_fail(self, report_fix):
        report, results, out_file_path = report_fix
        results.extend(
            [
                Result({
                    'result': 'fail',
                    }, "/fail")
                ]
            )
        report.go()

        do_assert(out_file_path, """<?xml version="1.0" ?>
<testsuites disabled="0" errors="0" failures="1" tests="1" time="0.0">
    <testsuite disabled="0" errors="0" failures="1" name="name" skipped="0" tests="1" time="0">
        <testcase name="/fail">
            <failure type="failure" message="fail"/>
        </testcase>
    </testsuite>
</testsuites>
""")
