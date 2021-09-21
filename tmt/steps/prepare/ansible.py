import click

import tmt


class PrepareAnsible(tmt.steps.prepare.PreparePlugin):
    """
    Prepare guest using ansible

    Single playbook config:

        prepare:
            how: ansible
            playbook: ansible/packages.yml

    Multiple playbooks config:

        prepare:
            how: ansible
            playbook:
              - playbook/one.yml
              - playbook/two.yml
              - playbook/three.yml
            extra-args: '-vvv'

    The playbook path should be relative to the metadata tree root.
    Use 'order' attribute to select in which order preparation should
    happen if there are multiple configs. Default order is '50'.
    Default order of required packages installation is '70'.
    """

    # Supported methods
    _methods = [tmt.steps.Method(name='ansible', doc=__doc__, order=50)]

    # Supported keys
    _keys = ["playbook", "extra-args"]

    def __init__(self, step, data):
        """ Store plugin name, data and parent step """
        super().__init__(step, data)
        # Rename plural playbooks to singular
        if 'playbooks' in self.data:
            self.data['playbook'] = self.data.pop('playbooks')

    @classmethod
    def options(cls, how=None):
        """ Prepare command line options """
        return [
            click.option(
                '-p', '--playbook', metavar='PLAYBOOK', multiple=True,
                help='Path to an ansible playbook to run.'),
            click.option(
                '--extra-args', metavar='EXTRA-ARGS',
                help='Optional arguments for ansible-playbook.')
            ] + super().options(how)

    def default(self, option, default=None):
        """ Return default data for given option """
        if option == 'playbook':
            return []
        return default

    def wake(self, keys=None):
        """ Wake up the plugin, process data, apply options """
        super().wake(keys=keys)

        # Convert to list if necessary
        tmt.utils.listify(self.data, keys=['playbook'])

    def go(self, guest):
        """ Prepare the guests """
        super().go(guest)

        # Apply each playbook on the guest
        for playbook in self.get('playbook'):
            self.info('playbook', playbook, 'green')
            guest.ansible(playbook, self.get('extra-args'))
