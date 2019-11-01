import unittest

from tmt.steps.execute import Execute, shell, beakerlib
from tmt.utils import SpecificationError


class TestExecute(unittest.TestCase):

    def test_data_empty(self):
        data = {}
        plan = None
        exe = Execute(data, plan)
        exe._check_data()
        self.assertEqual(exe.data['how'], 'shell')

    def test_invalid_data_list(self):
        data = [{'how': 'beakerlib', 'name': 'one'}, {'name': 'two'}]
        plan = None
        exe = Execute(data, plan)
        self.assertRaises(SpecificationError, exe._check_data)

    def test_invalid_data_unsupported_executor(self):
        data = {'how': 'whatever'}
        plan = None
        exe = Execute(data, plan)
        self.assertRaises(SpecificationError, exe._check_data)

    def test_pick_executor_shell(self, how='shell', executor=shell.ExecutorShell):
        plan = None
        data = {'how': how}
        exe = Execute(data, plan)
        exe.wake()
        self.assertIsInstance(exe.executor, executor)

    def test_pick_executor_empty(self):
        plan = None
        data = {}
        exe = Execute(data, plan)
        exe.wake()
        self.assertIsInstance(exe.executor, shell.ExecutorShell)

    def test_pick_executor_beakerlib(self):
        self.test_pick_executor_shell('beakerlib', beakerlib.ExecutorBeakerlib)


class ExecuteStepMock(object):
    pass


class TestShellExecutor(unittest.TestCase):

    def test_requires(self):
        data = {'how': 'shell'}
        plan = None
        execute = ExecuteStepMock()
        exe = shell.ExecutorShell(data, execute)
        self.assertEqual(exe.requires(), ())


class TestBeakerlibExecutor(unittest.TestCase):

    def test_requires(self):
        data = {'how': 'beakerlib'}
        plan = None
        execute = ExecuteStepMock()
        exe = beakerlib.ExecutorBeakerlib(data, execute)
        self.assertEqual(exe.requires(), ('beakerlib', ))
