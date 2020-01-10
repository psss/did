# coding: utf-8

""" Prepare Step Class """

import tmt
import os
import shutil
import subprocess
import re

from click import echo
from urllib.parse import urlparse

from tmt.utils import GeneralError, SpecificationError

class Prepare(tmt.steps.Step):
    name = 'prepare'

    valid_inputs = { 'shell': ['script'],
                     'ansible': ['playbook', 'playbooks']
                   }

    ## Default API ##
    def __init__(self, data, plan):
        """ Initialize the Prepare step """
        self.super = super(Prepare, self)
        self.super.__init__(data, plan)

    def wake(self):
        """ Wake up the step (process workdir and command line) """
        self.super.wake()

        for i in range(len(self.data)):
            self.opts(i, 'how', 'script')

            for alt in ('playbook', 'playbooks'):
                value = self.alias(i, 'script', alt)
                how = self.data[i]['how']

                if value and how in self.valid_inputs:
                    valid = self.valid_inputs[how]
                    if not alt in valid:
                        raise SpecificationError(f"You cannot specify {alt} for {how}.")

    def show(self):
        """ Show discover details """
        self.super.show(keys = ['how', 'script'])

    def go(self):
        """ Prepare the test step """
        # TODO: not sure why
        self.super.go()

        packages = []
        for step in self.plan.steps():
            if getattr(step, 'requires', False):
                packages += step.requires()

        if packages:
            self.debug(f'Installing steps requires', ', '.join(packages))
            self.install(packages)

        for dat in self.data:
            self.run_how(dat)


    ## Knowhow ##
    def run_how(self, dat):
        """ Run specific HOW """
        input = dat['script']
        if not input:
            self.debug('note', f"No data provided for prepare.", 'yellow')
            return
        self.debug('input', input, 'yellow')

        how = dat['how']
        getattr(self, f"how_{how}", self.how_generic)(how, input)

    def how_generic(self, how, what):
        """ Handle a generic 'Prepare',
            which is relayed to provider's prepare().
        """
        # Process multiple inputs
        if type(what) is list:
            return [self.how_generic(how, w) for w in what]

        # Try guesssing the path (1)
        whatpath = os.path.join(self.plan.run.tree.root, what)

        self.debug('Looking for prepare script in', whatpath)
        if os.path.exists(whatpath) and os.path.isfile(whatpath):
            what = whatpath
        else:
            # Try guesssing the path (2)
            whatpath = os.path.join(self.plan.workdir,
                'discover',
                self.data[0]['name'],
                'tests',
                what)

            self.debug('Looking for prepare script', whatpath)
            if os.path.exists(whatpath) and os.path.isfile(whatpath):
                what = whatpath

        try:
            self.plan.provision.prepare(how, what)
        except AttributeError as error:
            raise SpecificationError('NYI: cannot currently run this preparator.')


    ## Additional API ##
    def install(self, packages):
        """ Install specified package(s)
        """
        if type(packages) is list:
            packages = ' '.join(packages)

        ## TODO: remove this after run(shell=True) is in provision.prepare()
        try:
            self.plan.provision.prepare('shell', f"rpm -V {packages}")
        except GeneralError:
            self.plan.provision.prepare('shell', f"dnf install -y {packages}")
        return
        ## <

        failed = False
        logf = os.path.join(self.workdir, 'prepare.log')
        try:
            self.plan.provision.prepare('shell', f"set -o pipefail; ( rpm -V {packages} || sudo dnf install -y {packages} ) 2>&1 | tee -a '{logf}'")
        except GeneralError:
            failed = True

        self.plan.provision.sync_workdir_from_guest()

        output = open(logf).read()

        if failed:
            raise GeneralError(f'Install failed:\n{output}')

        self.debug(logf, output, 'yellow')


    ## END of API ##


    ## Helpers ##
    def set_default(self, i, where, default):
        """ Set `self.data[i]` entry if not set already or if empty.
            It needs an index specified as self.data is a list.
            Returns the value if set, '' otherwise.
        """
        if where in self.data[i] and self.data[i][where]:
            return ''
        else:
            self.data[i][where] = default
            return default

    def opts(self, i, *keys):
        """ Load opts into data[i][]
            It needs an index specified as self.data is a list.
            By the same key.
        """
        for key in keys:
            val = self.opt(key)
            if val:
                self.data[i][key] = val

    def alias(self, i, where, name):
        """ Maps additional data and opt entry onto a different one.
            It needs an index specified as self.data is a list.
            Actually Runs set_default based on entry in opt() and data[].
            Returns the selected value or ''
        """
        val = self.set_default(i, where, self.opt(name))

        if not val and name in self.data[i]:
            val = self.set_default(i, where, self.data[i][name])

        return val

    def get_uri(self, what):
        """ Return parsed URI if parsable,
            Otherwise returns ''.
            See is_uri().
        """
        if self.is_uri(what):
            what_uri = urlparse(what)
            for pr in ('netloc', 'path', 'query'):
                self.debug(f'URI {pr}', getattr(what_uri, pr))
            return what_uri
        else:
            return ''

    def is_uri(self, uri):
        """ Check if string is an URI-parsable
            actually returns its 'scheme'
        """
        return getattr(urlparse(uri),
            'scheme',
            None)

    def get_query(self, what_uri):
        """ Returns dict from parsed URI's query.
            See get_uri().
        """
        return dict(que.split("=") for que in what_uri.query.split("&"))

    def cmd_mkcd(self, target_dir):
        """ return string containing shell
            commands to create dir and copy a target in there
        """
        target_dir = self.quote(target_dir)
        return f'mkdir -p {target_dir}; cd {target_dir}'

    def quote(self, string):
        """ returns string decorated with squot """
        return f"'{string}'"

