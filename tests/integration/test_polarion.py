import os

import pytest
from click.testing import CliRunner
from fmf import Tree

import tmt.cli
from tmt.identifier import ID_KEY

from .test_nitrate import TEST_DIR, Base


@pytest.mark.skip(reason="Only works locally for now")
class PolarionExport(Base):
    EXAMPLES = TEST_DIR / "data" / "polarion"

    def test_create(self):
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn(ID_KEY, fmf_node.data)

        os.chdir(self.tmpdir / "new_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(tmt.cli.main, [
            "test", "export", "--how", "polarion", "--project-id",
            "RHIVOS", "--create", "."])
        # Reload the node data to see if it appears there
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertIn(ID_KEY, fmf_node.data)

    def test_create_dryrun(self):
        fmf_node_before = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn(ID_KEY, fmf_node_before.data)

        os.chdir(self.tmpdir / "new_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli.main,
            ["test", "export", "--how", "polarion", "--create", "--dry", "."],
            catch_exceptions=False)
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn(ID_KEY, fmf_node.data)
        self.assertEqual(fmf_node_before.data, fmf_node.data)
        self.assertIn(
            "title: tmt /new_testcase - This i",
            self.runner_output.output)

    def test_existing(self):
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(tmt.cli.main, [
            "test", "export", "--how", "polarion", "--project-id",
            "RHIVOS", "--create", "."])

        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

    def test_existing_dryrun(self):
        fmf_node = Tree(self.tmpdir).find("/existing_dryrun_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_dryrun_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli.main,
            ["test", "export", "--how", "polarion", "--debug", "--dry",
             "--bugzilla", "."],
            catch_exceptions=False)
        self.assertIn(
            "title: tmt /existing_dryrun_testcase - ABCDEF",
            self.runner_output.output)

    def test_coverage_bugzilla(self):
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(tmt.cli.main, [
            "test", "export", "--how", "polarion", "--project-id",
            "RHIVOS", "--bugzilla", "."])
        assert self.runner_output.exit_code == 0
