# coding: utf-8

""" Provision Step Vagrnat Class """

import tmt
import subprocess
import os
import re

from tmt.steps.provision.base import ProvisionBase
from tmt.utils import ConvertError, StructuredFieldError, SpecificationError

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
    config_prefix = '  config.vm.'
    sync_type = 'rsync'
    default_image = 'centos/7'
    default_container = 'centos:7'
    default_indent = 16
    image_uri = None
    timeout = 333
    eol = '\n'

    ## Default API ##
    def __init__(self, data, step):
        """ Initialize the Vagrant provision step """
        self.super = super(ProvisionVagrant, self)
        self.super.__init__(data, step)
        self.vagrantfile = os.path.join(self.provision_dir, 'Vagrantfile')
        self.vf_data = ''

        # Are we resuming?
        if os.path.exists(self.vagrantfile) and os.path.isfile(self.vagrantfile):
            self.validate()
            return

        # Check for working Vagrant
        self.run_vagrant('version')

        # Let's check what's needed
        self.check_how()

        # TODO: where should this run?
        self.init()

    def load(self):
        """ Load ProvisionVagrant step """
        #TODO: ensure this loads self.data[*]
        # instancename and regenerates provision_dir and vagrantfile
        self.super.load()

    def save(self):
        """ Save ProvisionVagrant step """
        #TODO: ensure this saves self.data[*]
        # instancename
        self.super.save()
        #TypeError: save() takes 1 positional argument but 2 were given

#    def wake(self):
#        """ Prepare the Vagrantfile """
#        self.super.wake(self)
#        # capabilities? providers?

    def go(self):
        """ Execute actual provisioning """
        self.info('Provisioning vagrant, Vagrantfile', self.vf_read())
        self.run_vagrant('up')

    def execute(self, cmd):
        """ Execute remote command """
        self.run_vagrant('ssh', '-c', cmd)

    def show(self):
        """ Show execute details """
        self.super.show(keys=['how', 'box', 'image'])
        self.info('Vagrantfile', self.vf_read())

    def sync_workdir_to_guest(self):
        """ sync on demand """
        # TODO: test
        self.run_vagrant('rsync')

    def sync_workdir_from_guest(self):
        """ sync from guest to host """
        raise ConvertError('NYI: cannot currently sync from guest.')

    def copy_from_guest(self, target):
        """ copy file/folder from guest to host's copy dir """
        beg = f"[[ -d '{target}' ]]"
        end = 'set -xe; exit 0; '

        isdir = f"{beg} || {end}"
        isntdir = f"{beg} && {end}"

        target_dir = f'{self.provision_dir}/copy/{target}'
        self.execute(isdir + self.cmd_mkcp(target_dir, f'{target}/.'))

        target_dir = f'$(dirname "{self.provision_dir}/copy/{target}")'
        self.execute(isntdir + self.cmd_mkcp(target_dir, target))

        self.sync_workdir_from_guest()

    def destroy(self):
        """ remove instance """
        self.run_vagrant('destroy', '-f')

    def prepare(self, name, path):
        """ add single 'preparator' and run it """
        raise ConvertError('NYI: cannot currently add preparators.')
        self.add_config('provision', name, 'path')


    ## Additional API ##
    def init(self):
        """ Initialize Vagrantfile """
        # Create a Vagrantfile
        self.create()

        # Add default entries to Vagrantfile
        self.add_defaults()

        # Let's add what's needed
        self.add_how()

    def create(self):
        """ Create default Vagrantfile with our modifications """
        self.run_vagrant('init', '-fm', self.data['box'])
        self.info('Initialized new Vagrantfile', self.vf_read())
        self.validate()

    def status(self):
        """ Get vagrant's status """
        raise ConvertError('NYI: cannot currently return status.')
        # TODO: how to get stdout from self.run?
        #csp = self.run_vagrant('status')
        #return self.hr(csp.stdout)

    def clean(self):
        """ remove box and base box """
        self.run_vagrant('box', 'remove', '-f', self.data['box'])
        # TODO: libvirt storage removal?

    def validate(self):
        """ Validate Vagrantfile format """
        self.run_vagrant('validate')

    def reload(self):
        """ restart guest """
        self.run_vagrant('reload')


    ## Knowhow ##
    def check_how(self):
        """ Decide what to do when HOW is ...
            does not add anything into Vagrantfile yet
        """
        self.debug('Checking initial status, setting defaults.')

        self.set_default('how', 'virtual')
        self.set_default('image', self.default_image)

        image = self.data['image']

        try:
            i = urlparse(image)
            if not i.schema:
                raise (i)
            self.image_uri = i
        except:
            pass

        self.info('image_uri', self.image_uri)

        if self.image_uri:
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

        for x in ('how','box','image'):
            self.info(x, self.data[x])

    def add_how(self):
        target = f"how_{self.data['how']}"
        self.debug(f"Relaying to: {target}")
        getattr(self,
            target,
            lambda: 'generic',
            )()

    def how_virtual(self):
        self.debug(f"generating: virtual")
        # let's just do libvirt for now
        self.how_libvirt()

    def how_generic():
        self.debug(f"generating: generic")
        self.add_provider_config(self.data['how'])

    def how_libvirt(self):
        self.debug(f"generating: libvirt")
        self.vf_backup()
        try:
            self.debug(f"Trying QEMU session.")
            self.add_provider_config('libvirt', 'qemu_use_session = true')
        except:
            self.vf_restore()

    def how_openstack(self):
        self.debug(f"generating: openstack")
        raise SpecificationError('NYI: cannot currently run on openstack.')

    def how_docker(self):
        self.how_container()

    def how_podman(self):
        self.how_container()

    def how_container(self):
        self.debug(f"generating: container")
        raise SpecificationError('NYI: cannot currently run containers.')


    ## END of API ##
    def add_defaults(self):
        """ Adds default config entries
            1) Disable default sync
            2) To sync plan workdir
        """
        self.add_synced_folder(".", "/vagrant", 'disabled: true')

        dir = self.step.plan.workdir
        self.add_synced_folder(dir, dir)

    def run_vagrant(self, *args):
        """ Run vagrant command and raise an error if it fails

              args = 'command args'

            or

              args = ['comand', 'args']

        """
        if len(args) == 0:
            raise RuntimeError("vagrant has to run with args")

        cmd = self.prepend(args, self.executable)

#            timeout = self.timeout,
        cps = self.run(
            cmd,
            cwd = self.provision_dir)

    def add_synced_folder(self, sync_from, sync_to, *args):
        self.add_config('synced_folder',
            self.quote(sync_from),
            self.quote(sync_to),
            f'type: {self.quote(self.sync_type)}', *args)

    def add_provider_config(self, provider, *config):
        config_str = ''
        for c in config:
          config_str += f'{provider}.{c}; '

        self.add_raw_config(f"provider '{provider}' do |{provider}| {config_str}; end")

    def add_config(self, *config):
        """ Add config entry into Vagrantfile

              config = "string"

            or:

              config = ['one', 'two', 'three']
                => one "two", three

            see add_raw_config
        """
        if len(config) == 1:
            config = config[0]
        elif len(config) == 0:
            raise RuntimeError("config has no definition")
        else:
            config = f'{config[0]} ' + ', '.join(config[1:])

        self.add_raw_config(config)

    def add_raw_config(self, config):
        """ Add arbitrary config entry into Vagrantfile
            right before last 'end'.
            Prepends with `config_prefix`.
        """
        self.info('Adding into Vagrantfile', [config])

        vf_tmp = self.vf_read()

        # Lookup last 'end' in Vagrantfile
        i = 0
        for line in reversed(vf_tmp):
            i -= 1
            if (line.find('end') != -1):
                break

        vf_tmp = vf_tmp[:i] \
            + [self.config_prefix + config] \
            + vf_tmp[i:]

        self.vf_write(vf_tmp)

    def vf_read(self):
        """ read Vagrantfile
            also splits
        """
        return open(self.vagrantfile).read().splitlines()

    def vf_write(self, vf_tmp):
        """ write into Vagrantfile
            str or list
            runs validate()
        """
        if type(vf_tmp) is list:
            vf_tmp = self.eol.join(vf_tmp)

        with open(self.vagrantfile, 'w', newline=self.eol) as f:
            f.write(vf_tmp)

        self.validate()

    def vf_backup(self):
        """ backup Vagrantfile contents to vf_data """
        self.vf_data = self.vf_read()

    def vf_restore(self):
        """ restore Vagrantfile contents frmo vf_data"""
        self.debug('Restoring Vagrantfile from memory.')
        self.vf_write(self.vf_data)


    ## Helpers ##
    def info(self, key = '', val = '', color = 'green'):
        """ info out!
            see msgout()
        """
        self.msgout('debug', key, val, color)

    def debug(self, key = '', val = '', color='yellow'):
        """ debugging, yay!
            see msgout()
        """
        self.msgout('debug', key, val, color)

    def msgout(self, mtype, key = '', val = '', color = 'Red'):
        """ args: key, value, indent, color
            all optional
        """
        # Avoid unneccessary processing
        if self.opt(mtype) or self.opt('debug'):
            if type(val) is list and len(val):
                ind_val = self.eol
                for v in val:
                    if v:
                        ind_val += ' '*self.default_indent + self.hr(v) + self.eol

                val = ind_val
            else:
                val = self.hr(val)

            emsg = lambda: RuntimeError(f"Message type unknown: {mtype}")

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
        """ return human readable data """
        if type(val) is tuple or type(val) is list:
            ret = ''
            for v in val:
                ret += self.hr(v)
            return ret

        if type(val) is bytes:
            val = str(val, "utf-8")

        try:
            val = rstrip(val)
            eol = self.eol
        except:
            eol = ''

        return f'{val}{eol}'

    def set_default(self, where, default):
        if not (where in self.data and self.data[where]):
            self.data[where] = default

    def prepend(self, thing, string):
        if type(thing) is list:
            return thing.insert(0, string)
        elif type(thing) is tuple:
            return (string ,) + thing
        else:
            return string + ' ' + thing

    def append(self, thing, string):
        if type(thing) is list:
            return thing.append(string)
        elif type(thing) is tuple:
            return thing + (string ,)
        else:
            return thing + ' ' + string

    def cmd_mkcp(self, target_dir, target):
        target_dir = self.quote(target_dir)
        target = self.quote(target)
        return f'mkdir -p {target_dir}; cp -vafr {target} {target_dir}'

    def quote(self, string):
        return f'"{string}"'
