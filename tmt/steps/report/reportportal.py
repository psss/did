import dataclasses
import io
import os
import types
import zipfile
from typing import List, Optional

import click

import tmt.steps.report
import tmt.utils

from . import junit

junit_xml: Optional[types.ModuleType] = None


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


@dataclasses.dataclass
class ReportReportPortalData(tmt.steps.report.ReportStepData):
    url: Optional[str] = None
    project: Optional[str] = None
    token: Optional[str] = None
    launch_name: Optional[str] = None


@tmt.steps.provides_method("reportportal")
class ReportReportPortal(tmt.steps.report.ReportPlugin):
    """
    Send results in JUnit format to a ReportPortal instance

    Requires a TOKEN for authentication, a URL of the ReportPortal instance and
    the PROJECT name. The optional launch NAME is passed to ReportPortal.

    Assuming the URL and TOKEN variables are provided by the environment, the
    config can look like this:

        report:
            how: reportportal
            project: baseosqe
            launch-name: maven
    """

    _data_class = ReportReportPortalData

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options """
        return [
            click.option(
                "--url", envvar="TMT_REPORT_REPORTPORTAL_URL", metavar="URL", required=True,
                help="The URL of the ReportPortal instance where the data should be sent to."),
            click.option(
                "--project", metavar="PROJECT", required=True,
                help="The project name which is used to create the full URL."),
            click.option(
                "--token", envvar="TMT_REPORT_REPORTPORTAL_TOKEN", metavar="TOKEN", required=True,
                help="The token to use for upload to the ReportPortal instance."),
            click.option(
                "--launch-name", metavar="NAME",
                help="The launch name."),
            ] + super().options(how)

    def go(self) -> None:
        """
        Read executed tests, prepare junit, compress it to a zip zile and
        send it to the ReportPortal instance.
        """

        super().go()

        import_junit_xml()
        assert junit_xml is not None
        suite = junit.make_junit_xml(self)
        data = junit_xml.TestSuite.to_xml_string([suite])
        bytestream = io.BytesIO()

        with zipfile.ZipFile(bytestream, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=1) as zipstream:
            # XML file names are irrelevant to ReportPortal
            with zipstream.open("tests.xml", "w") as entry:
                entry.write(data.encode("utf-8"))
        bytestream.seek(0)

        with tmt.utils.retry_session() as session:
            assert self.step.plan.my_run is not None
            assert self.step.plan.my_run._workdir is not None
            launch_name = self.get("launch_name") or os.path.basename(
                self.step.plan.my_run._workdir)
            url = self.get("url") + "/api/v1/" + self.get("project") + "/launch/import"
            response = session.post(
                url,
                headers={
                    "Authorization": "bearer " + self.get("token"),
                    "accept": "*/*",
                    },
                files={
                    # The zip filename is used as the launch name in ReportPortal
                    "file": (launch_name + ".zip", bytestream, "application/zip"),
                    },
                )

        if not response.ok:
            message = response.json().get("message")
            if message is None:
                message = response.text
            raise tmt.utils.ReportError(
                "Received non-ok status code from ReportPortal, response text is: " + message)
        else:
            self.info("output", "Response code: " + str(response.status_code), "yellow")
