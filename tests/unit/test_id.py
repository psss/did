import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

import fmf
from click.testing import CliRunner

import tmt
import tmt.cli
from tmt.identifier import ID_KEY, locate_key

runner = CliRunner()
test_path = Path(__file__).parent / "id"


class IdLocationDefined(TestCase):
    def setUp(self) -> None:
        self.base_tree = fmf.Tree(test_path / "defined")

    def test_defined(self):
        node = self.base_tree.find("/yes")
        self.assertEqual(
            locate_key(node, ID_KEY), node)

    def test_defined_partially(self):
        node = self.base_tree.find("/partial")
        test = tmt.Test(node)
        self.assertEqual(locate_key(node, ID_KEY), test.node)

    def test_not_defined(self):
        node = self.base_tree.find("/deep/structure/no")
        self.assertEqual(locate_key(node, ID_KEY).name, "/deep")

    def test_deeper(self):
        node = self.base_tree.find("/deep/structure/yes")
        self.assertEqual(node, locate_key(node, ID_KEY))

    def test_deeper_not_defined(self):
        node = self.base_tree.find("/deep/structure/no")
        self.assertNotEqual(node, locate_key(node, ID_KEY))
        self.assertEqual(locate_key(node, ID_KEY).name, "/deep")


class IdLocationEmpty(TestCase):
    def setUp(self) -> None:
        self.base_tree = fmf.Tree(test_path / "empty")

    def test_defined_root(self):
        node = self.base_tree.find("/")
        self.assertEqual(locate_key(node, ID_KEY), None)

    def test_defined(self):
        node = self.base_tree.find("/some/structure")
        self.assertEqual(locate_key(node, ID_KEY), None)


class IdEmpty(TestCase):

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "empty"
        shutil.copytree(test_path / "empty", self.path)
        self.original_directory = Path.cwd()
        os.chdir(self.path)
        self.base_tree = fmf.Tree(self.path)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.path)

    def test_base(self):
        node = self.base_tree.find("/some/structure")
        test = tmt.Test(node)
        self.assertEqual(test.id, None)

    def test_manually_add_id(self):
        node = self.base_tree.find("/some/structure")
        test = tmt.Test(node)
        self.assertEqual(test.id, None)
        identifier = tmt.identifier.add_uuid_if_not_defined(node, dry=False)
        self.assertGreater(len(identifier), 10)

        self.base_tree = fmf.Tree(self.path)
        node = self.base_tree.find("/some/structure")
        test = tmt.Test(node)
        self.assertEqual(test.id, identifier)


class TestGeneratorDefined(TestCase):

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "defined"
        shutil.copytree(test_path / "defined", self.path)
        self.original_directory = Path.cwd()
        os.chdir(self.path)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.path)

    def test_test_dry(self):
        result = runner.invoke(
            tmt.cli.main, ["test", "id", "--dry", "^/no"])
        self.assertIn("added to test '/no", result.output)
        result = runner.invoke(
            tmt.cli.main, ["test", "id", "--dry", "^/no"])
        self.assertIn("added to test '/no", result.output)

    def test_test_real(self):
        # Empty before
        node = fmf.Tree(self.path).find("/no")
        self.assertEqual(node.get(ID_KEY), None)

        # Generate only when called for the first time
        result = runner.invoke(tmt.cli.main, ["test", "id", "^/no"])
        self.assertIn("added to test '/no", result.output)
        result = runner.invoke(tmt.cli.main, ["test", "id", "^/no"])
        self.assertNotIn("added to test '/no", result.output)

        # Defined after
        node = fmf.Tree(self.path).find("/no")
        self.assertGreater(len(node.data[ID_KEY]), 10)


class TestGeneratorEmpty(TestCase):

    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "empty"
        shutil.copytree(test_path / "empty", self.path)
        self.original_directory = Path.cwd()
        os.chdir(self.path)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.path)

    def test_test_dry(self):
        result = runner.invoke(
            tmt.cli.main, ["test", "id", "--dry"])
        self.assertIn(
            "added to test '/some/structure'",
            result.output)
        result = runner.invoke(
            tmt.cli.main, ["test", "id", "--dry"])
        self.assertIn(
            "added to test '/some/structure'",
            result.output)

    def test_test_real(self):
        result = runner.invoke(tmt.cli.main, ["test", "id"])
        self.assertIn(
            "added to test '/some/structure'",
            result.output)

        result = runner.invoke(tmt.cli.main, ["test", "id"])
        self.assertNotIn(
            "added to test '/some/structure'",
            result.output)

        base_tree = fmf.Tree(self.path)
        node = base_tree.find("/some/structure")
        self.assertGreater(len(node.data[ID_KEY]), 10)
