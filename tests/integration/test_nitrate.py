import os
import shutil
import tempfile
from pathlib import Path

from click.testing import CliRunner
from fmf import Tree
from requre import RequreTestCase
from ruamel.yaml import YAML

import tmt.base
import tmt.cli

# Prepare path to examples
TEST_DIR = Path(__file__).parent
NITRATE_EXAMPLE = TEST_DIR / "data" / "nitrate"


class Base(RequreTestCase):
    def setUp(self):
        super().setUp()
        self.tmpdir = Path(tempfile.mktemp(prefix=str(TEST_DIR)))
        shutil.copytree(NITRATE_EXAMPLE, self.tmpdir)
        self.cwd = os.getcwd()
        self.runner_output = None

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.chdir(self.cwd)
        super().tearDown()
        if hasattr(
                self.runner_output,
                "exit_code") and self.runner_output.exit_code != 0:
            print("Return code:", self.runner_output.exit_code)
            print("Output:", self.runner_output.output)
            print("Exception:", self.runner_output.exception)


# General test plan for this component is: TP#29309
class NitrateExport(Base):

    def test_create(self):
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn("extra-nitrate", fmf_node.data)

        os.chdir(self.tmpdir / "new_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(tmt.cli.main, [
            "test", "export", "--nitrate", "--create", "--general", "."])
        # Reload the node data to see if it appears there
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertIn("extra-nitrate", fmf_node.data)

    def test_existing(self):
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_testcase")
        runner = CliRunner()
        self.runner_output = runner.invoke(tmt.cli.main,
                                           ["test", "export", "--nitrate",
                                            "--create", "--general", "."])
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")

        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")


class NitrateImport(Base):

    def test_import_manual_confirmed(self):
        runner = CliRunner()
        # TODO: import does not respect --root param anyhow (could)
        self.runner_output = runner.invoke(
            tmt.cli.main,
            ['-vvvvdddd', '--root', self.tmpdir / "import_case",
             "test", "import", "--nitrate", "--manual", "--case=609704"])
        self.assertEqual(self.runner_output.exit_code, 0)
        self.assertIn(
            "Importing the 'Imported_Test_Case'",
            self.runner_output.output)
        self.assertIn(
            "test case found 'TC#0609704'",
            self.runner_output.output)
        self.assertIn(
            "Metadata successfully stored into",
            self.runner_output.output)
        filename = next(
            filter(
                lambda x: "Metadata successfully stored into" in x and "main.fmf" in x,
                self.runner_output.output.splitlines())).split("'")[1]
        # /home/jscotka/git/tmt/Manual/Imported_Test_Case/main.fmf
        # TODO: not possible to specify, where to store data,
        # it always creates Manual subdir, I do not want it.
        self.assertIn("/Manual/Imported_Test_Case/main.fmf", filename)
        self.assertTrue(Path(filename).exists())
        with open(Path(filename)) as file:
            yaml = YAML(typ='safe')
            out = yaml.load(file)
            self.assertIn("Tier1", out["tag"])
            self.assertIn("tmt_test_component", out["component"])

    def test_import_manual_proposed(self):
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli.main, ['--root', self.tmpdir / "import_case", "test",
                           "import", "--nitrate", "--manual", "--case=609705"])
        self.assertEqual(self.runner_output.exit_code, 0)
        # TODO: This is strange, expect at least some output in
        # case there is proper case, just case is not CONFIRMED
        # I can imagine also e.g. at least raise error but not pass,
        # with no output
        self.assertEqual(self.runner_output.output.strip(), "")
        fmf_node = Tree(self.tmpdir).find("/import_case")
        self.assertEqual(fmf_node, None)


class NitrateImportAutomated(Base):
    test_md_content = """# Setup
Do this and that to setup the environment.

# Test

## Step
Step one.

Step two.

Step three.

## Expect
Expect one.

Expect two

Expect three.

# Cleanup
This is a breakdown.
"""
    main_fmf_content = """summary: Simple smoke test
description: |
    Just run 'tmt --help' to make sure the binary is sane.
    This is really that simple. Nothing more here. Really.
contact: Petr Šplíchal <psplicha@redhat.com>
component:
- tmt
test: ./runtest.sh
framework: beakerlib
require:
- fmf
recommend:
- tmt
duration: 5m
enabled: true
tag: []
link:
-   relates: https://bugzilla.redhat.com/show_bug.cgi?id=12345
-   relates: https://bugzilla.redhat.com/show_bug.cgi?id=1234567
adjust:
-   because: comment
    enabled: false
    when: distro == rhel-4, rhel-5
    continue: false
-   environment:
        PHASES: novalgrind
    when: arch == s390x
    continue: false
extra-nitrate: TC#0609926
extra-summary: /tmt/integration
extra-task: /tmt/integration
"""

    def test_basic(self):
        os.chdir(self.tmpdir / "import_case_automated")
        files = os.listdir()
        self.assertIn("Makefile", files)
        self.assertNotIn("main.fmf", files)
        self.assertNotIn("test.md", files)
        runner = CliRunner()
        self.runner_output = runner.invoke(
            tmt.cli.main, ["test", "import", "--nitrate"])
        self.assertEqual(self.runner_output.exit_code, 0)
        files = os.listdir()
        self.assertIn("Makefile", files)
        self.assertIn("test.md", files)
        with open("test.md") as file:
            self.assertIn(self.test_md_content, file.read())
        self.assertIn("main.fmf", files)
        with open("main.fmf") as file:
            yaml = YAML(typ='safe')
            generated = yaml.load(file)
            referenced = yaml.load(self.main_fmf_content)
            self.assertEqual(generated, referenced)
