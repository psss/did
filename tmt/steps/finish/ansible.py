import tmt
import tmt.steps
import tmt.steps.finish
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

    # Assigning class methods seems to cause trouble to mypy
    # See also: https://github.com/python/mypy/issues/6700
    base_command = tmt.steps.finish.FinishPlugin.base_command  # type: ignore
