# coding: utf-8

import os
import fmf
import tmt.cli
import tempfile
import shutil

from click.testing import CliRunner

# Prepare path to examples
PATH = os.path.dirname(os.path.realpath(__file__))
CONVERT = os.path.join(PATH, "../../examples/convert")

runner = CliRunner()

def test_convert():
    """ Convert old metadata """
    tmp = tempfile.mkdtemp()
    os.system('cp -a {} {}'.format(CONVERT, tmp))
    path = os.path.join(tmp, 'convert')
    command = 'test import --no-nitrate {}'.format(path)
    result = runner.invoke(tmt.cli.main, command.split())
    assert result.exit_code == 0
    assert 'Metadata successfully stored' in result.output
    assert 'This is really that simple' in result.output
    node = fmf.Tree(path).find('/')
    assert node.get('summary') == 'Simple smoke test'
    assert node.get('component') == ['tmt']
    assert 'This is really that simple.' in node.get('description')
    shutil.rmtree(tmp)
