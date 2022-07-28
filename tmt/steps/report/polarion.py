import datetime
import os
import xml.etree.ElementTree as ET
from typing import Any, List, Optional

import click
from requests import post

import tmt

from .junit import make_junit_xml

DEFAULT_NAME = 'xunit.xml'


class ReportPolarion(tmt.steps.report.ReportPlugin):
    """
    Write test results into a xUnit file and upload to Polarion
    """
    _methods = [tmt.steps.Method(name='polarion', doc=__doc__, order=50)]
    _keys = ['file', 'no-upload', 'project-id', 'testrun-title']

    @classmethod
    def options(cls, how: Optional[str] = None) -> List[tmt.options.ClickOptionDecoratorType]:
        """ Prepare command line options """
        options = super().options(how)
        options[:0] = [
            click.option(
                '--file', metavar='FILE', help='Path to the file to store xUnit in'),
            click.option(
                '--upload / --no-upload', default=True, show_default=True,
                help="Whether to upload results to Polarion"),
            click.option(
                '--project-id', required=True, help='Use specific Polarion project ID'),
            click.option(
                '--testrun-title', help='Use specific TestRun title')
            ]
        return options

    def go(self, *args: Any, **kwargs: Any) -> None:
        """ Go through executed tests and report into Polarion """
        super().go()

        from tmt.export import get_polarion_ids, import_polarion
        import_polarion()
        from tmt.export import PolarionWorkItem
        assert PolarionWorkItem

        title = self.opt(
            'testrun_title',
            self.step.plan.name.rsplit('/', 1)[1] +
            datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        title = title.replace('-', '_')
        project_id = self.opt('project-id')
        upload = self.opt('upload')

        junit_suite = make_junit_xml(self)
        xml_tree = ET.fromstring(junit_suite.to_xml_string([junit_suite]))

        properties = {
            'polarion-project-id': project_id,
            'polarion-user-id': PolarionWorkItem._session.user_id,
            'polarion-testrun-id': title,
            'polarion-project-span-ids': project_id}
        testsuites_properties = ET.SubElement(xml_tree, 'properties')
        for name, value in properties.items():
            ET.SubElement(testsuites_properties, 'property', attrib={
                'name': name, 'value': value})

        testsuite = xml_tree.find('testsuite')
        project_span_ids = xml_tree.find(
            '*property[@name="polarion-project-span-ids"]')

        for result in self.step.plan.execute.results():
            if not result.id:
                raise tmt.utils.ReportError(
                    f"Test Case {result.name} is not exported to Polarion, "
                    "please run 'tmt tests export --how polarion' on it")
            work_item_id, test_project_id = get_polarion_ids(
                PolarionWorkItem.query(
                    result.id, fields=['work_item_id', 'project_id']))

            assert work_item_id is not None
            assert test_project_id is not None
            assert project_span_ids is not None

            if test_project_id not in project_span_ids.attrib['value']:
                project_span_ids.attrib['value'] += f',{test_project_id}'

            test_properties = {
                'polarion-testcase-id': work_item_id,
                'polarion-testcase-project-id': test_project_id}

            assert testsuite is not None
            test_case = testsuite.find(f"*[@name='{result.name}']")
            assert test_case is not None
            properties_elem = ET.SubElement(test_case, 'properties')
            for name, value in test_properties.items():
                ET.SubElement(properties_elem, 'property', attrib={
                    'name': name, 'value': value})

        assert self.workdir is not None

        f_path = self.opt("file", os.path.join(self.workdir, DEFAULT_NAME))
        with open(f_path, 'wb') as fw:
            ET.ElementTree(xml_tree).write(fw)

        if upload:
            server_url = str(PolarionWorkItem._session._server.url)
            polarion_import_url = (
                f'{server_url}{"" if server_url.endswith("/") else "/"}'
                'import/xunit')
            auth = (
                PolarionWorkItem._session.user_id,
                PolarionWorkItem._session.password)

            response = post(
                polarion_import_url, auth=auth,
                files={'file': ('xunit.xml', ET.tostring(xml_tree))})
            self.info(
                f'Response code is {response.status_code} with text: {response.text}')
        else:
            self.info(f"xUnit file saved at: {f_path}")
            self.info("Polarion upload can be done manually using command:")
            self.info(
                "curl -k -u <USER>:<PASSWORD> -X POST -F file=@<XUNIT_XML_FILE_PATH> "
                "<POLARION_URL>/polarion/import/xunit")
