import tmt
import tmt.steps.finish
from tmt.steps.prepare.ansible import PrepareAnsible


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

    # Supported methods
    _methods = [tmt.steps.Method(name='ansible', doc=__doc__, order=50)]

    # Explicitly use these from FinishPlugin class
    _supported_methods = tmt.steps.finish.FinishPlugin._supported_methods
    base_command = tmt.steps.finish.FinishPlugin.base_command
