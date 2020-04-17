# coding: utf-8

""" Provision Step Vagrnat Class """

import tmt
import subprocess
import os
import re
import shutil
from time import sleep

from tmt.steps.provision.base import ProvisionBase
from tmt.utils import ConvertError, SpecificationError, GeneralError, quote

from click import echo
from urllib.parse import urlparse


# DATA[*]:
#   HOW = libvirt|virtual|docker|container|vagrant|...
#         provider, in Vagrant's terminilogy
#
#   IMAGE = URI|NAME
#         NAME is for Vagrant or other HOW, passed directly
#         URI can be path to BOX, QCOW2 or Vagrantfile f.e.
#
#   BOX = Set a BOX name directly (in case of URI for IMAGE)
#
class ProvisionVagrant(ProvisionBase):
    """ Use Vagrant to Provision an environment for testing """
    executable = 'vagrant'
    config_prefix = '  config.'
    sync_type = 'rsync'
    default_image = 'fedora/31-cloud-base'
    dummy_image = 'tknerr/managed-server-dummy'
    default_container = 'fedora:latest'
    default_indent = 16
    default_user = 'root'
    default_memory = 2048
    vf_name = 'Vagrantfile'
    timeout = 333
    eol = '\n'
    display = ('how', 'image', 'key', 'guest', 'memory')
    statuses = ('not reachable', 'running', 'not created', 'preparing')


    ## Default API ##
    def __init__(self, data, step):
        """ Initialize the Vagrant provision step """
        self.super = super(ProvisionVagrant, self)
        self.super.__init__(data, step)
        self.vagrantfile = os.path.join(self.provision_dir, self.vf_name)
        self.vf_data = ''
        self.path = os.path.join(self.provision_dir, 'data.yaml')

        # Which opts do we recieve
        self.opts('image', 'box', 'memory', 'user', 'password', 'key',
            'guest', 'vagrantfile')

        self.debugon = self.opt('debug')

    def load(self):
        """ Load ProvisionVagrant step """
        raise SpecificationError("NYI: cannot load")
        self.super.load()

    def save(self):
        """ Save ProvisionVagrant step """
        raise SpecificationError("NYI: cannot save")
        self.super.save()

    def go(self):
        """ Execute actual provisioning """
        self.init()
        self.info(
            f'Provisioning {self.executable}, {self.vf_name}', self.vf_read())
        out, err = self.run_vagrant('up')

        status = self.status()
        if status != 'running':
            raise GeneralError(
                f'Failed to provision (status: {status}), log:\n{out}\n{err}')

    def execute(self, *args, **kwargs):
        """ Execute remote command """
        return self.run_vagrant('ssh', '-c', self.join(args))

    def show(self):
        """ Create and show the Vagrantfile """
        self.super.show(
            keys=['how', 'box', 'image', 'memory', 'user', 'password'])
        self.info(self.vf_name, self.vf_read())

    def sync_workdir_to_guest(self):
        """ sync on demand """
        return self.run_vagrant('rsync')

    def sync_workdir_from_guest(self):
        """ sync from guest to host """
        command = 'rsync-back'
        self.plugin_install(command)
        return self.run_vagrant(command)

    def destroy(self):
        """ remove instance """
        for i in range(1, 5):
            if i > 1 and self.status() == 'not created':
                return
            try:
                return self.run_vagrant('destroy', '-f')
            except GeneralError:
                sleep(5)

    def prepare(self, how, what):
        """ add single 'preparator' and run it """

        name = 'prepare'
        cmd = 'provision'

        self.vf_backup("Prepare")

        # decide what to do
        if how == 'ansible':
            name = how

            # Prepare verbose level based on the --debug option count
            verbose = self.opt('debug') * 'v' if self.opt('debug') else 'false'
            self.add_config_block(cmd,
                name,
                f'become = true',
                self.kve('become_user', self.data['user']),
                self.kve('playbook', what),
                self.kve('verbose', verbose))
                # I'm not sure whether this is needed:
                # run: 'never'

        else:
            if self.is_uri(what):
                method = 'path'
            else:
                method = 'inline'

            self.add_config('vm',
                cmd,
                quote(name),
                self.kv('type', how),
                self.kv('privileged', 'true'),
                self.kv('run', 'never'),
                self.kv(method, what))

        try:
            self.validate()
        except GeneralError as error:
            self.vf_restore()
            raise GeneralError(
                f'Invalid input for vagrant prepare ({how}):\n{what}')

        return self.run_vagrant(cmd, f'--{cmd}-with', name)


    ## Additional API ##
    def init(self):
        """ Initialize ProvisionVagrant / run following:
            1] check that Vagrant works
            2] check for already-present or user-specified Vagrantfile
            3] check input values and set defaults
            4] create and populates Vagrantfile with
                - provider-specific entries
                - default config entries
        """
        self.debug('provision dir', self.provision_dir)

         # Check for working Vagrant
        self.run_vagrant('version')

        # Let's check what's needed
        self.check_input()

        # Are we resuming?
        if os.path.exists(self.vagrantfile) and os.path.isfile(self.vagrantfile):
            self.validate()
            return

        # Did we get a Vagranfile?
        if 'vagrantfile' in self.data:
            shutil.copyfile(self.data['vagrantfile'], self.vagrantfile)
            self.validate()
            return

        # Let's add what's needed
        # Important: run this first to install provider
        self.add_how()

        # Add default entries to Vagrantfile
        self.add_defaults()

    def create(self):
        """ Initialize Vagrantfile """
        self.run_vagrant('init', '-fm', self.data['box'])
        self.debug('Initialized new Vagrantfile', self.vf_read())

    def clean(self):
        """ remove box and base box """
        return self.run_vagrant('box', 'remove', '-f', self.data['box'])
        # TODO: libvirt storage removal?

    def validate(self):
        """ Validate Vagrantfile format """
        return self.run_vagrant('validate')

    def reload(self):
        """ restart guest machine """
        return self.run_vagrant('reload')

    def status(self):
        """ check guest status """
        out, err = self.run_vagrant('status')

        for status in self.statuses:
            if not re.search(f" {status} ", out) is None:
                return status
        return 'unknown'

    def plugin_install(self, name):
        """ Install a vagrant plugin if it's not installed yet.
        """
        plugin = f'{self.executable}-{name}'
        command = ['plugin', 'install']
        try:
            # is it already present?
            run = f"{self.executable} {command[0]} list | grep '^{plugin} '"
            return self.run(f"bash -c \"{run}\"")
        except GeneralError:
            pass

        try:
            # try to install it
            return self.run_vagrant(command[0], command[1], plugin)
        except GeneralError as error:
            # Let's work-around the error handling limitation for now
            # by getting the output manually
            command = ' '.join([self.executable] + command + [plugin])

            out, err = self.run(f"bash -c \"{command}; :\"")

            if re.search(r"Conflicting dependency chains:", err) is None:
                raise error
            raise GeneralError('Dependency conflict detected:\n'
                'Please install vagrant plugins from one source only (hint: `dnf remove rubygem-fog-core`).')


    ## Knowhow ##
    def check_input(self):
        """ Initialize configuration(sets defaults), based on data (how, image).
            does not create Vagrantfile or add anything into it.
        """
        self.debug('VagrantProvider', 'Checking initial status, setting defaults.')

        self.set_default('how', 'virtual')
        self.set_default('image', self.default_image)

        image = self.data['image']

        if self.is_uri(image):
            self.set_default('box', 'box_' + self.instance_name)

            if re.search(r"\.box$", image) is None:
                # an actual box file, Great!
                pass

            elif re.search(r"\.qcow2$", image) is None:
                # do some qcow2 magic
                self.data['box'] = '...'
                raise SpecificationError("NYI: QCOW2 image")

            else:
                raise SpecificationError(f"Image format not recognized: {image}")

        else:
            self.set_default('box', image)
            self.data['image'] = None

        self.set_default('memory', self.default_memory)

        # General ssh config, used for 'managed' as well
        self.set_default('user', self.default_user)

        for key, val in self.data.items():
            if self.debugon or key in self.display:
                if not val is None:
                    self.info(f'{key}', val)

    def add_how(self):
        """ Add provider (in Vagrant-speak) specifics """
        getattr(self,
            f"how_{self.data['how']}",
            self.how_generic,
            )()
        self.validate()

    def how_generic(self):
        self.debug("generating", "generic")
        self.create()
        self.add_provider(self.data['how'])

    def how_libvirt(self):
        """ Add libvirt provider specifics into Vagrantfile
             - try adding QEMU session entry
        """
        name = 'libvirt'
        self.debug("generating", name)

        self.plugin_install(name)

        self.gen_virtual(name)

        self.vf_backup("QEMU user session")
        self.add_provider(name, 'qemu_use_session = true')

        try:
            self.validate()
        except GeneralError as error:
            self.vf_restore()
            # Not really an error
            #self.debug(error)

    def how_connect(self):
        """ Defines a connection to guest
            using managed provider from managed-servers plugin.
            Recreates Vagrantfile with dummy box.
        """
        name = 'connect'
        self.debug("generating", name)

        guest = self.data['guest']
        if guest is None:
            raise SpecificationError('Guest is not specified.')
        self.debug("guest", guest)

        self.plugin_install(f"managed-servers")

        self.data['box'] = self.dummy_image
        self.create()

        self.add_provider('managed', self.kve('server', guest))

        # Let's use the config.ssh setup first; this is backup:
        # => override.ssh.username
        # => override.ssh.private_key_path = ".vagrant/machines/local_linux/virtualbox/private_key"

    def how_container(self):
        self.debug("generating", "container")
        raise SpecificationError('NYI: cannot currently run containers.')

    def how_openstack(self):
        self.debug("generating", "openstack")
        raise SpecificationError('NYI: cannot currently run on openstack.')

    # Aliases
    def how_docker(self):
        self.how_container()

    def how_podman(self):
        self.how_container()

    def how_virtual(self):
        self.how_libvirt()


    ## END of API ##
    def gen_virtual(self, provider = ''):
        """ Add config entry for VM
            (re)creates Vagrantfile with
             - box
             - box_url
             - memory and provider(if provider is set)
        """
        self.create()

        image = self.data['image']
        if image:
            self.add_config('vm', self.kve("box_url", image))

        if provider:
            self.add_provider(provider, self.kve('memory', self.data['memory']))

    def add_defaults(self):
        """ Adds default /generic/ config entries into Vagrantfile:
             - disable default sync
             - add sync for plan.workdir
             - add ssh config opts if set
             - disable nfs check
            and validates Vagrantfile
        """
        self.add_synced_folder(".", "/vagrant", 'disabled: true')

        dir = self.step.plan.workdir
        self.add_synced_folder(dir, dir)

        # Credentials are used for `how: connect` as well as for VMs
        if 'user' in self.data:
          self.add_config('ssh', self.kve('username', self.data['user']))
        if 'password' in self.data:
            self.add_config('ssh', self.kve('password', self.data['password']))
        if 'key' in self.data:
            self.add_config('ssh', self.kve('private_key_path', self.data['key']))

        self.add_config('nfs', 'verify_installed = false')

        # Enabling this fails with `how: connect`
        #self.add_config('ssh', 'insert_key = false')
        self.validate()

    def run_vagrant(self, *args):
        """ Run vagrant command and raise an error if it fails
              args = 'command args'
            or
              args = ['comand', 'args']
        """
        if len(args) == 0:
            raise RuntimeError("vagrant has to run with args")

        cmd = self.prepend(args, self.executable)

        # TODO: timeout = self.timeout,
        return self.run(cmd, cwd=self.provision_dir, shell=False)

    def add_synced_folder(self, sync_from, sync_to, *args):
        """ Add synced_folder entry into Vagrantfile """
        self.add_config('vm',
            'synced_folder',
            quote(sync_from),
            quote(sync_to),
            self.kv('type', self.sync_type),
            *args)

    def add_provider(self, provider, *config):
        """ Add provider entry into Vagrantfile """
        self.add_config_block('provider', provider, *config)

    def add_config_block(self, name, block, *config):
        """ Add a config block into Vagrantfile
        """
        config_str = ''
        for c in config:
            config_str += f'{block}.{c}; '

        self.add_config('vm', f"{name} '{block}' do |{block}| {config_str}end")

    def add_config(self, type, *config):
        """ Add config entry into Vagrantfile right before last 'end',
            and prepends it with `config_prefix`.

            Adding arbitrary config entry:
                config = "string"
            or, with conversion:
                config = ['one', 'two', 'three']
                => one "two", three
        """
        if len(config) == 1:
            config = config[0]
        elif len(config) == 0:
            raise RuntimeError("config has no definition")
        else:
            config = f'{config[0]} ' + ', '.join(config[1:])

        self.debug('Adding into Vagrantfile', f"{type}.{config}", 'green')

        vf_tmp = self.vf_read()

        # Lookup last 'end' in Vagrantfile
        i = 0
        for line in reversed(vf_tmp):
            i -= 1
            # TODO: avoid infinite loop in case of invalid Vagrantfile
            if (line.find('end') != -1):
                break

        vf_tmp = vf_tmp[:i] \
            + [self.config_prefix + f"{type}." + config] \
            + vf_tmp[i:]

        self.vf_write(vf_tmp)

    def vf_read(self):
        """ read Vagrantfile
            also splits lines
        """
        return open(self.vagrantfile).read().splitlines()

    def vf_write(self, vf_tmp):
        """ write into Vagrantfile
            str or list
        """
        if type(vf_tmp) is list:
            vf_tmp = self.eol.join(vf_tmp)

        with open(self.vagrantfile, 'w', newline=self.eol) as f:
            f.write(vf_tmp)

    def vf_backup(self, msg=''):
        """ backup Vagrantfile contents to vf_data """
        if msg:
            self.info("Trying to enable", msg)
        self.msg = msg
        self.vf_data = self.vf_read()

    def vf_restore(self):
        """ restore Vagrantfile contents from vf_data"""
        if self.msg:
            self.info('Reverting', self.msg, 'red')
            self.msg = ''
        self.vf_write(self.vf_data)


    ## Helpers ##
    def info(self, key = '', val = '', color = 'green'):
        """ info out!
            see msgout()
        """
        self.msgout('info', key, val, color)

    def debug(self, key = '', val = '', color='yellow'):
        """ debugging, yay!
            see msgout()
        """
        self.msgout('debug', key, val, color)

    def msgout(self, mtype, key = '', val = '', color = 'red'):
        """ args: key, value, indent, color
            all optional
        """
        if type(val) is list and len(val):
            ind_val = ''
            for v in val:
                if v:
                    ind_val += ' '*self.default_indent + self.hr(v) + self.eol

            val = ind_val
        else:
            val = self.hr(val)

        emsg = lambda: RuntimeError(f"Message type unknown: {mtype}")

        # Call super.debug or super.info
        if val:
            getattr(self.super,
                mtype,
                emsg,
                )(key, val, color)
        else:
            getattr(self.super,
                mtype,
                emsg,
                )(key)

    def hr(self, val):
        """ return human readable data
             - converts bytes, tuples and lists
             - separates entries with newlines
             - runs recursively
             - tries to add eol
        """
        if type(val) is tuple or type(val) is list:
            ret = ''
            for v in val:
                ret += self.hr(v)
            return ret

        if type(val) is bytes:
            val = str(val, "utf-8")

        elif type(val) is not str:
            val = str(val)

        try:
            val = rstrip(val)
            eol = self.eol
        except:
            eol = ''

        return f'{val}{eol}'

    def set_default(self, where, default):
        """ Set `self.data` entry if not set already or if empty """
        if not (where in self.data and self.data[where]):
            self.data[where] = default

    def prepend(self, thing, string):
        """ modify object to prepend it with string
            based on the type of object
             - tuple, list, string
             - adds a space for string
        """
        if type(thing) is list:
            return thing.insert(0, string)
        elif type(thing) is tuple:
            return (string ,) + thing
        else:
            return string + ' ' + thing

    def is_uri(self, uri):
        """ Check if string is an URI-parsable
            actually returns its 'scheme'
        """
        return getattr(urlparse(uri),
            'scheme',
            None)

    def kv(self, key, val, sep=': '):
        """ returns key-value decrorated
             - use separator
             - quote val
        """
        return f'{key}{sep}{quote(val)}'

    def kve(self, key, val, sep=' = '):
        """ returns key equals value
            see kv()
        """
        return self.kv(key, val, sep)

    def opts(self, *keys):
        """ Load opts into data[]
            By the same key.
            see opt()
        """
        for key in keys:
            val = self.opt(key)
            if val:
                self.data[key] = val

    def opt(self, key):
        """ Return option specified on commandline """
        return self.step.plan.provision.opt(key)
