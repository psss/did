# coding: utf-8

import os
import tmt
import shutil
import tempfile
import click.testing

runner = click.testing.CliRunner()

def test_invalid_yaml_syntax():
    """ Invalid yaml syntax """
    tmp = tempfile.mkdtemp()
    original_directory = os.getcwd()
    os.chdir(tmp)
    result = runner.invoke(tmt.cli.main, ['init', '--template', 'mini'])
    with open('plans/example.fmf', 'a') as plan:
        plan.write('bad line')
    result = runner.invoke(tmt.cli.main)
    assert isinstance(result.exception, tmt.utils.GeneralError)
    assert result.exit_code != 0
    os.chdir(original_directory)
    shutil.rmtree(tmp)
