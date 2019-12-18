# coding: utf-8

import os
import shutil
import tmt.cli
import tempfile

from click.testing import CliRunner

# Prepare path to examples
PATH = os.path.dirname(os.path.realpath(__file__))
MINI = os.path.join(PATH, "../../examples/mini")
SYSTEMD = os.path.join(PATH, "../../examples/systemd")

runner = CliRunner()

def test_mini():
    """ Minimal smoke test """
    result = runner.invoke(tmt.cli.main,
        ['--root', MINI, 'run', '--debug', 'provision', '--how=local'])
    assert result.exit_code == 0
    assert 'Found 1 plan.' in result.output
    assert '/ci/test/build/smoke' in result.output

def test_init():
    """ Tree initialization """
    tmp = tempfile.mkdtemp()
    original_directory = os.getcwd()
    os.chdir(tmp)
    result = runner.invoke(tmt.cli.main, ['init'])
    assert 'initialized' in result.output
    result = runner.invoke(tmt.cli.main, ['init'])
    assert 'already exists' in result.output
    result = runner.invoke(tmt.cli.main, ['init', '--mini'])
    assert 'plans/example' in result.output
    result = runner.invoke(tmt.cli.main, ['init', '--mini'])
    assert result.exception
    result = runner.invoke(tmt.cli.main, ['init', '--full', '--force'])
    assert 'overwritten' in result.output
    # tmt init --mini in a clean directory
    os.system('rm -rf .fmf *')
    result = runner.invoke(tmt.cli.main, ['init', '--mini'])
    assert 'plans/example' in result.output
    # tmt init --full in a clean directory
    os.system('rm -rf .fmf *')
    result = runner.invoke(tmt.cli.main, ['init', '--full'])
    assert 'tests/example' in result.output
    os.chdir(original_directory)
    shutil.rmtree(tmp)

def test_create():
    """ Test, plan and story creation """
    # Create a test directory
    tmp = tempfile.mkdtemp()
    original_directory = os.getcwd()
    os.chdir(tmp)
    # Commands to test
    commands = [
        'init',
        'test create -t beakerlib test',
        'test create -t shell test',
        'plan create -t mini test',
        'plan create -t full test',
        'story create -t mini test',
        'story create -t full test',
        ]
    for command in commands:
        result = runner.invoke(tmt.cli.main, command.split())
        assert result.exit_code == 0
        os.system('rm -rf *')
    # Test directory cleanup
    os.chdir(original_directory)
    shutil.rmtree(tmp)

def test_no_metadata():
    """ No metadata found """
    tmp = tempfile.mkdtemp()
    result = runner.invoke(tmt.cli.main, ['--root', tmp, 'run'])
    assert result.exception
    os.rmdir(tmp)

def test_step():
    """ Select desired step"""
    for step in tmt.steps.STEPS:
        if step == 'provision':
            continue
        result = runner.invoke(tmt.cli.main, [
            '--root', MINI, 'run', '--all', 'provision', '--how=local', step
        ])
        assert result.exit_code == 0
        assert step in result.output
        assert 'Provision' not in result.output

def test_systemd():
    """ Check systemd example """
    result = runner.invoke(tmt.cli.main, ['--root', SYSTEMD, 'plan'])
    assert result.exit_code == 0
    assert 'Found 2 plans' in result.output
    result = runner.invoke(tmt.cli.main, ['--root', SYSTEMD, 'plan', 'show'])
    assert result.exit_code == 0
    assert 'Tier two functional tests' in result.output
