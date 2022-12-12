import dataclasses
import io
import os
import types
import zipfile
from typing import Optional

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
    url: Optional[str] = tmt.utils.field(
        option="--url",
        metavar="URL",
        default=os.environ.get("TMT_REPORT_REPORTPORTAL_URL"),
        help="The URL of the ReportPortal instance where the data should be sent to.")
    token: Optional[str] = tmt.utils.field(
        option="--token",
        metavar="TOKEN",
        default=os.environ.get("TMT_REPORT_REPORTPORTAL_TOKEN"),
        help="The token to use for upload to the ReportPortal instance.")
    project: Optional[str] = tmt.utils.field(
        option="--project",
        metavar="PROJECT",
        default=None,
        help="The project name which is used to create the full URL.")
    launch_name: Optional[str] = tmt.utils.field(
        option="--launch-name",
        metavar="NAME",
        default=None,
        help="The launch name (base name of run id used by default).")


@tmt.steps.provides_method("reportportal")
class ReportReportPortal(tmt.steps.report.ReportPlugin):
    """
    Report test results to a ReportPortal instance

    Requires a TOKEN for authentication, a URL of the ReportPortal
    instance and the PROJECT name. In addition to command line options
    it's possible to use environment variables to set the url and token:

        export TMT_REPORT_REPORTPORTAL_URL=...
        export TMT_REPORT_REPORTPORTAL_TOKEN=...

    The optional launch NAME is passed to ReportPortal. Assuming the URL
    and TOKEN variables are provided by the environment, the config can
    look like this:

        report:
            how: reportportal
            project: baseosqe
            launch-name: maven
    """

    _data_class = ReportReportPortalData

    def go(self) -> None:
        """
        Read executed tests, prepare junit, compress it to a zip zile and
        send it to the ReportPortal instance.
        """

        super().go()

        # Check the data, show interesting info to the user
        # Required fields are: url, token and project
        server = self.get("url")
        if not server:
            raise tmt.utils.ReportError("No ReportPortal server url provided.")
        server = server.rstrip("/")

        token = self.get("token")
        if not token:
            raise tmt.utils.ReportError("No ReportPortal token provided.")

        project = self.get("project")
        if not project:
            raise tmt.utils.ReportError("No ReportPortal project provided.")
        self.info("project", project, color="green")

        # Use provided launch name, default to run workdir name
        assert self.step.plan.my_run is not None
        assert self.step.plan.my_run.workdir is not None
        launch_name = self.get("launch-name") or os.path.basename(self.step.plan.my_run.workdir)
        self.info("launch", launch_name, color="green")

        # Generate a xUnit report
        import_junit_xml()
        assert junit_xml is not None
        suite = junit.make_junit_xml(self)
        data = junit_xml.TestSuite.to_xml_string([suite])

        # Zip the report
        bytestream = io.BytesIO()
        with zipfile.ZipFile(bytestream, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=1) as zipstream:
            # XML file names are irrelevant to ReportPortal
            with zipstream.open("tests.xml", "w") as entry:
                entry.write(data.encode("utf-8"))
        bytestream.seek(0)

        # Send the report to the ReportPortal instance
        with tmt.utils.retry_session() as session:
            url = f"{server}/api/v1/{project}/launch/import"
            self.debug(f"Send the report to '{url}'.")
            response = session.post(
                url,
                headers={
                    "Authorization": "bearer " + token,
                    "accept": "*/*",
                    },
                files={
                    # The zip filename is used as the launch name in ReportPortal
                    "file": (launch_name + ".zip", bytestream, "application/zip"),
                    },
                )

        # Handle the response
        try:
            message = tmt.utils.yaml_to_dict(response.text).get("message")
        except (tmt.utils.GeneralError, KeyError):
            message = response.text
        if not response.ok:
            raise tmt.utils.ReportError(
                f"Received non-ok status code from ReportPortal, response text is: {message}")
        else:
            self.debug(f"Response code from the server: {response.status_code}")
            self.debug(f"Message from the server: {message}")
            self.info("report", "Successfully uploaded.", "yellow")
