import yaml
import shutil
import tempfile
from fmf import Tree
from pathlib import Path
from click.testing import CliRunner
from requre import RequreTestCase
import tmt.base
import tmt.cli
import os

# Prepare path to examples
TEST_DIR = Path(__file__).parent
NITRATE_EXAMPLE = TEST_DIR / "data" / "nitrate"


# general test plan for this component is: TP#29309
class NitrateExport(RequreTestCase):

    def setUp(self):
        super().setUp()
        self.tmpdir = Path(tempfile.mktemp())
        shutil.copytree(NITRATE_EXAMPLE, self.tmpdir)
        self.cwd = os.getcwd()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        os.chdir(self.cwd)
        super().tearDown()

    def test_create(self):
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertNotIn("extra-nitrate", fmf_node.data)

        os.chdir(self.tmpdir / "new_testcase")
        runner = CliRunner()
        output = runner.invoke(tmt.cli.main, [ "test", "export", "--nitrate", "--create", "--general", "."])
        print(output)
        # reload the node data to see if it appear there
        fmf_node = Tree(self.tmpdir).find("/new_testcase")
        self.assertIn("extra-nitrate", fmf_node.data)

    def test_existing(self):
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")
        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")

        os.chdir(self.tmpdir / "existing_testcase")
        runner = CliRunner()
        runner.invoke(
            tmt.cli.main, ["test", "export", "--nitrate", "--create", "--general", "."])
        fmf_node = Tree(self.tmpdir).find("/existing_testcase")

        self.assertEqual(fmf_node.data["extra-nitrate"], "TC#0609686")


class NitrateImport(RequreTestCase):

    def setUp(self):
        super().setUp()
        self.tmpdir = Path(tempfile.mktemp())
        shutil.copytree(NITRATE_EXAMPLE, self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        super().tearDown()

    def test_import_manual_confirmed(self):
        runner = CliRunner()
        # TODO: import does not respect --root param anyhow (could)
        result = runner.invoke(
            tmt.cli.main, ['-vvvvdddd', '--root', self.tmpdir / "import_case", "test",
                           "import", "--nitrate", "--manual",
                           "--case=609704"])
        print(result.output)
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Importing the 'Imported_Test_Case'", result.output)
        self.assertIn("test case found 'TC#0609704'", result.output)
        self.assertIn("Metadata successfully stored into", result.output)
        filename = next(filter(lambda x:
                               "Metadata successfully stored into"
                               in x and "main.fmf" in x,
                               result.output.splitlines())).split("'")[1]
        # /home/jscotka/git/tmt/Manual/Imported_Test_Case/main.fmf
        # TODO: not possible to specify, where to store data,
        #  it always creates Manual subdir, I do not want it.
        self.assertIn("/Manual/Imported_Test_Case/main.fmf", filename)
        self.assertTrue(Path(filename).exists())
        with open(Path(filename)) as fd:
            out = yaml.safe_load(fd)
            self.assertIn("Tier1", out["tag"])
            self.assertIn("tmt_test_component", out["component"])

    def test_import_manual_proposed(self):
        runner = CliRunner()
        result = runner.invoke(
            tmt.cli.main, ['--root', self.tmpdir / "import_case", "test",
                           "import", "--nitrate", "--manual", "--case=609705"])
        self.assertEqual(result.exit_code, 0)
        # TODO: This is strange, expect at least some output in
        #  case there is proper case, just case is not CONFIRMED
        #  I can imagine also e.g. at least raise error but not pass,
        #  with no output
        self.assertEqual(result.output.strip(), "")
        fmf_node = Tree(self.tmpdir).find("/import_case")
        self.assertEqual(fmf_node, None)
