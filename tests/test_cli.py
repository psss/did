# coding: utf-8

from __future__ import unicode_literals, absolute_import

import os
import tmt.cli

from click.testing import CliRunner

# Prepare path to examples
PATH = os.path.dirname(os.path.realpath(__file__))
MINI = os.path.join(PATH, "../examples/mini")
SYSTEMD = os.path.join(PATH, "../examples/systemd")

runner = CliRunner()

def test_mini():
    """ Minimal smoke test """
    result = runner.invoke(tmt.cli.main, ['--path', MINI])
    assert result.exit_code == 0
    assert 'Found 1 testset.' in result.output
    assert 'Testset: /ci/test/build/smoke' in result.output

def test_step():
    """ Select desired step"""
    for step in tmt.steps.STEPS:
        result = runner.invoke(tmt.cli.main, ['--path', MINI, step])
        assert result.exit_code == 0
        assert step.capitalize() in result.output
        if step != 'provision':
            assert 'Provision' not in result.output

def test_systemd():
    """ Check systemd example """
    result = runner.invoke(tmt.cli.main, ['--path', SYSTEMD])
    assert result.exit_code == 0
    assert 'Found 2 testsets.' in result.output
    assert 'Tier two functional tests' in result.output
