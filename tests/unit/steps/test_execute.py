import pytest

import fmf
import tmt
import tmt.plugins

# Load all plugins
tmt.plugins.explore()

# Ignore loading/saving from/to workdir
tmt.steps.execute.Execute.load = lambda self: None
tmt.steps.execute.Execute.save = lambda self: None


# Smoke plan
smoke = tmt.Plan(fmf.Tree({'execute': {'script': 'tmt --help'}}))
smoke.execute.wake()

def test_smoke_method():
    assert smoke.execute.data[0]['how'] == 'tmt'

def test_smoke_plugin():
    assert isinstance(
        smoke.execute.plugins()[0], tmt.steps.execute.ExecutePlugin)

def test_requires():
    assert smoke.execute.requires() == []


# Basic plan
basic = tmt.Plan(fmf.Tree({'execute': {'how': 'beakerlib'}}))
basic.execute.wake()

def test_basic_method():
    assert basic.execute.data[0]['how'] == 'tmt'

def test_basic_plugin():
    assert isinstance(
        basic.execute.plugins()[0], tmt.steps.execute.ExecutePlugin)

def test_basic_requires():
    assert basic.execute.requires() == ['beakerlib']


# Invalid plan
def test_multiple_data():
    data = [{'how': 'beakerlib', 'name': 'one'}, {'name': 'two'}]
    executor = tmt.steps.execute.Execute(data, plan=smoke)
    with pytest.raises(tmt.utils.SpecificationError):
        executor.wake()

def test_unsupported_executor():
    data = {'how': 'whatever'}
    executor = tmt.steps.execute.Execute(data, plan=smoke)
    with pytest.raises(tmt.utils.SpecificationError):
        executor.wake()
