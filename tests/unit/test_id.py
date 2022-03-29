# coding: utf-8
import os
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase

import fmf
from click.testing import CliRunner

import tmt
import tmt.cli
from tmt.uuid import ID_FMF_ITEM, IDError, IDLeafError, locate_key

runner = CliRunner()
test_path = Path(__file__).parent / "test_fmf_id"


class IDLocationDefined(TestCase):
    def setUp(self) -> None:
        self.base_tree = fmf.Tree(test_path / "defined")

    def test_defined(self):
        node = self.base_tree.find("/yes")
        self.assertEqual(
            locate_key(node, ID_FMF_ITEM), node)

    def test_defined_partially(self):
        node = self.base_tree.find("/partial")
        test = tmt.Test(node)
        self.assertEqual(locate_key(node, ID_FMF_ITEM), test.node)

    def test_not_defined(self):
        node = self.base_tree.find("/no")
        self.assertEqual(locate_key(node, ID_FMF_ITEM).name, "/")

    def test_deeper(self):
        node = self.base_tree.find("/deep/structure/yes")
        self.assertEqual(node, locate_key(node, ID_FMF_ITEM))

    def test_deeper_not_defined(self):
        node = self.base_tree.find("/deep/structure/no")
        self.assertNotEqual(node, locate_key(node, ID_FMF_ITEM))
        self.assertEqual(locate_key(node, ID_FMF_ITEM).name, "/deep")


class IDLocationEmpty(TestCase):
    def setUp(self) -> None:
        self.base_tree = fmf.Tree(test_path / "empty")

    def test_defined_root(self):
        node = self.base_tree.find("/")
        self.assertEqual(locate_key(node, ID_FMF_ITEM), None)

    def test_defined(self):
        node = self.base_tree.find("/some/structure")
        self.assertEqual(locate_key(node, ID_FMF_ITEM), None)


class IDEmpty(TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()
        shutil.copytree(test_path / "empty", self.path, dirs_exist_ok=True)
        self.original_directory = Path.cwd()
        os.chdir(self.path)
        self.base_tree = fmf.Tree(self.path)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.path)

    def test_base(self):
        node = self.base_tree.find("/some/structure")
        test = tmt.Test(node)
        with self.assertRaises(IDLeafError):
            print(test.id)

    def test_manually_add_id(self):
        node = self.base_tree.find("/some/structure")
        test = tmt.Test(node)
        try:
            id = test.id
            self.assertFalse(True, "This should not happen")
        except IDError:
            id = tmt.uuid.add_uuid_if_not_defined(node, dry=False)
        self.assertGreater(len(id), 10)

        self.base_tree = fmf.Tree(self.path)
        node = self.base_tree.find("/some/structure")
        test = tmt.Test(node)
        try:
            id = test.id
            self.assertTrue(True, "This has to happen")
        except IDError:
            self.assertFalse(True, "This should not happen")
        self.assertGreater(len(id), 10)


class TestGeneratorDefined(TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()
        shutil.copytree(test_path / "defined", self.path, dirs_exist_ok=True)
        self.original_directory = Path.cwd()
        os.chdir(self.path)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.path)

    def test_test_dry(self):
        result = runner.invoke(
            tmt.cli.main, ["test", "uuid", "--dry"])
        self.assertIn(
            'Add new ID to test node /deep/structure/no =',
            result.output)
        result = runner.invoke(
            tmt.cli.main, ["test", "uuid", "--dry"])
        self.assertIn(
            'Add new ID to test node /deep/structure/no =',
            result.output)

    def test_test_real(self):
        result = runner.invoke(tmt.cli.main, ["test", "uuid"])
        self.assertIn(
            'Add new ID to test node /deep/structure/no =',
            result.output)

        result = runner.invoke(tmt.cli.main, ["test", "uuid"])
        self.assertNotIn(
            'Add new ID to test node /deep/structure/no =',
            result.output)

        base_tree = fmf.Tree(test_path / "defined")
        node = base_tree.find("/no")
        print(node.data)
        self.assertEqual(
            node.data.get(ID_FMF_ITEM),
            'a38cdf1e-066a-4a03-8da8-65005138ad92')
        # Not defined in leaf
        with node as data:
            self.assertEqual(data.get(ID_FMF_ITEM), None)

        base_tree = fmf.Tree(self.path)
        node = base_tree.find("/no")
        self.assertNotEqual(
            node.data.get(ID_FMF_ITEM),
            'a38cdf1e-066a-4a03-8da8-65005138ad92')
        self.assertGreater(len(node.data[ID_FMF_ITEM]), 10)


class TestGeneratorEmpty(TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()
        shutil.copytree(test_path / "empty", self.path, dirs_exist_ok=True)
        self.original_directory = Path.cwd()
        os.chdir(self.path)

    def tearDown(self):
        os.chdir(self.original_directory)
        shutil.rmtree(self.path)

    def test_test_dry(self):
        result = runner.invoke(
            tmt.cli.main, ["test", "uuid", "--dry"])
        self.assertIn(
            'Add new ID to test node /some/structure =',
            result.output)
        result = runner.invoke(
            tmt.cli.main, ["test", "uuid", "--dry"])
        self.assertIn(
            'Add new ID to test node /some/structure =',
            result.output)

    def test_test_real(self):
        result = runner.invoke(tmt.cli.main, ["test", "uuid"])
        self.assertIn(
            'Add new ID to test node /some/structure =',
            result.output)

        result = runner.invoke(tmt.cli.main, ["test", "uuid"])
        self.assertNotIn(
            'Add new ID to test node /some/structure =',
            result.output)

        base_tree = fmf.Tree(self.path)
        node = base_tree.find("/some/structure")
        self.assertGreater(len(node.data[ID_FMF_ITEM]), 10)
