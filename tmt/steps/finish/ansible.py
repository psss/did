import tmt.steps
import tmt.steps.finish
import tmt.steps.prepare.ansible
from tmt.steps.prepare.ansible import PrepareAnsible


@tmt.steps.provides_method('ansible')
class FinishAnsible(tmt.steps.finish.FinishPlugin, PrepareAnsible):
    """
    Perform finishing tasks using ansible

    Single playbook config:

        finish:
            how: ansible
            playbook: ansible/packages.yml

    Multiple playbooks config:

        finish:
            how: ansible
            playbook:
              - playbook/one.yml
              - playbook/two.yml
              - playbook/three.yml

    The playbook path should be relative to the metadata tree root.
    Use 'order' attribute to select in which order finishing tasks
    should happen if there are multiple configs. Default order is '50'.
    """

    # We are re-using "prepare" step for "finish",
    # and they both have different expectations
    _data_class = tmt.steps.prepare.ansible.PrepareAnsibleData  # type: ignore[assignment]

    # Assigning class methods seems to cause trouble to mypy
    # See also: https://github.com/python/mypy/issues/6700
    base_command = tmt.steps.finish.FinishPlugin.base_command  # type: ignore[assignment]
