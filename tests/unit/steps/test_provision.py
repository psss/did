import os
import pytest
import unittest
import tempfile

from mock import MagicMock, patch

from tmt.steps.provision import Provision, localhost, vagrant
from tmt.utils import GeneralError, SpecificationError


class PlanMock(MagicMock):
    workdir = tempfile.mkdtemp()
    # this is required with older mock
    run = MagicMock(tree=MagicMock(root=''))

    def opt(self, *args, **kwargs):
        return {}

    def _level(self):
        return 0


def test_empty_plan():
    provision = Provision({}, None)
    with pytest.raises(GeneralError):
        provision.wake()


def test_defaults():
    provision = Provision({}, PlanMock())
    provision.wake()
    for provision_data in provision.data:
        assert provision_data['how'] == 'virtual'


@pytest.mark.parametrize('how,provisioner', [
    ('libvirt', vagrant.ProvisionVagrant),
    ('virtual', vagrant.ProvisionVagrant),
    ('vagrant', vagrant.ProvisionVagrant),
    ('local', localhost.ProvisionLocalhost),
    ('localhost', localhost.ProvisionLocalhost)
])
def test_pick_provision(how, provisioner):
    plan = PlanMock()
    provision = Provision({'how': how}, plan)
    provision.wake()
    for guest in provision.guests:
        assert isinstance(guest, provisioner)


def test_localhost_execute():
    plan = PlanMock()
    provision = Provision({'how': 'localhost'}, plan)
    provision.wake()

    with patch('tmt.utils.Common.run') as run:
        provision.execute('a', 'b', 'c')
        run.assert_called_once_with('a b c')


def test_localhost_prepare_ansible():
    plan = PlanMock()
    provision = Provision({'how': 'localhost'}, plan)
    provision.wake()

    with patch('tmt.utils.Common.run') as run:
        provision.prepare('ansible', 'playbook.yml')
        playbook = os.path.join(plan.run.tree.root, 'playbook.yml')
        run.assert_called_once_with(
            f'ansible-playbook -vb -c local -i localhost, {playbook}')


def test_localhost_prepare_shell():
    plan = PlanMock()
    provision = Provision({'how': 'localhost'}, plan)
    provision.wake()

    with patch('tmt.utils.Common.run') as run:
        provision.prepare('shell', 'a b c')
        run.assert_called_once_with('a b c', cwd=plan.run.tree.root)
