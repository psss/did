import os
import pytest
import unittest
import tempfile

from mock import MagicMock, patch

import tmt
from tmt.steps.provision import Provision, local
from tmt.utils import GeneralError, SpecificationError



class PlanMock(MagicMock):
    workdir = tempfile.mkdtemp()
    # this is required with older mock
    run = MagicMock(tree=MagicMock(root=''))

    def opt(self, *args, **kwargs):
        return None

    def _level(self):
        return 0


def test_defaults():
    provision = Provision({}, PlanMock())
    provision.wake()
    for provision_data in provision.data:
        assert provision_data['how'] == 'virtual'

import tmt.steps.provision.testcloud
import tmt.steps.provision.podman
import tmt.steps.provision.connect
import tmt.steps.provision.local

@pytest.mark.parametrize('how,provisioner', [
    ('local', tmt.steps.provision.local.ProvisionLocal),
    ('virtual', tmt.steps.provision.testcloud.ProvisionTestcloud),
    ('container', tmt.steps.provision.podman.ProvisionPodman),
    ('connect', tmt.steps.provision.connect.ProvisionConnect),
])
def test_pick_provision(how, provisioner):
    plan = PlanMock()
    provision = Provision({'how': how}, plan)
    provision.wake()
    for guest in provision.guests():
        assert isinstance(guest, tmt.base.Guest)


def test_localhost_execute():
    plan = PlanMock()
    guest = tmt.steps.provision.local.GuestLocal(
        {'guest': 'localhost'}, 'default', plan)

    with patch('tmt.utils.Common.run') as run:
        guest.execute(['a', 'b', 'c'])
        run.assert_called_once_with(['a', 'b', 'c'])


def test_localhost_prepare_ansible():
    plan = PlanMock()
    guest = tmt.steps.provision.local.GuestLocal(
        {'guest': 'localhost'}, 'default', plan)

    with patch('tmt.utils.Common.run') as run:
        run.return_value = ('out', 'err')
        guest.ansible('playbook.yml')
        playbook = os.path.join(plan.run.tree.root, 'playbook.yml')
        run.assert_called_once_with(
            f'sudo sh -c "stty cols {tmt.utils.OUTPUT_WIDTH}; '
            f'ansible-playbook -c local -i localhost, {playbook}"')
