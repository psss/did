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
    image_uri = None
    timeout = 333
    default_indent = 9
    eol = '\n'
    vf_data = ''
    verbose = False

    ## Default API ##
    def __init__(self, data, step):
        """ Initialize the Vagrant provision step """
        super(ProvisionVagrant, self).__init__(data, step)
        self.vagrantfile = os.path.join(self.provision_dir, 'Vagrantfile')

        self.verbose = bool(self.opt('verbose'))

        # Are we resuming?
        if os.path.exists(self.vagrantfile) and os.path.isfile(self.vagrantfile):
            self.validate()
            return self

        # Check for working Vagrant
        self.run_vagrant('version')

        # Let's check what's actually needed
        self.how()

        # Create a Vagrantfile
        self.create()

        # Add default entries to Vagrantfile
        self.add_defaults()

        # Let's check what's actually needed
        #self.add_knowhow()

    def load(self):
        """ Load ProvisionVagrant step """
        #TODO: ensure this loads self.data[*]
        # instancename and regenerates provision_dir and vagrantfile
        super(ProvisionVagrant, self).load()

    def save(self):
        """ Save ProvisionVagrant step """
        #TODO: ensure this saves self.data[*]
        # instancename
        super(ProvisionVagrant, self).save()
        #TypeError: save() takes 1 positional argument but 2 were given

#    def wake(self):
#        """ Prepare the Vagrantfile """
#        super(ProvisionVagrant, self).wake(self)
#        # capabilities? providers?

    def go(self):
        """ Execute actual provisioning """
        self.debug()
        self.verbose = True
        self.debug('Provisioning vagrant, this is the Vagrantfile:')
        self.debug('Vagrantfile', self.vf_read())
        return self.run_vagrant_success('up')

    def execute(self, cmd):
        """ Execute remote command """
        return self.run_vagrant_success('ssh', '-c', cmd)

    def show(self):
        """ Show execute details """
        super(ProvisionVagrant, self).show(keys=['how', 'box', 'image'])
        self.debug('Vagrantfile', self.vf_read())

    def sync_workdir_to_guest(self):
        """ sync on demand """
        # TODO: test
        return self.run_vagrant_success('rsync')

    def sync_workdir_from_guest(self):
        """ sync from guest to host """
        raise SpecificationError('NYI: cannot currently sync from guest.')

    def destroy(self):
        """ remove instance """
        return self.run_vagrant_success('destroy', '-f')

    def run_prepare(self, name, path):
        """ add single 'preparator' and run it """
        raise SpecificationError('NYI: cannot currently add preparators.')
        return self.add_config('provision', name, 'path')


    ## Additional API ##
    def create(self):
        """ Create default Vagrantfile with our modifications """
        self.run_vagrant_success('init', '-fm', self.data['box'])
        self.validate()

    def status(self):
        """ Get vagrant's status """
        csp = self.run_vagrant_success('status')
        return self.hr(csp.stdout)

    def cleanup(self):
        """ remove box and base box """
        return self.run_vagrant_success('box', 'remove', '-f', self.data['box'])
        # TODO: libvirt storage removal?

    def validate(self):
        """ Validate Vagrantfile format """
        return self.run_vagrant_success('validate')

    def reload(self):
        """ restart guest """
        return self.run_vagrant_success('reload')


    ## Knowhow ##
    def how(self):
        """ Decide what to do when HOW is ...
            does not add anything into Vagrantfile yet
        """
        self.debug()

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

        self.debug('image_uri', self.image_uri)

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
            self.debug(x, self.data[x])

        # TODO: Dynamic call [switch] to specific how_*
        return True

    def how_virtual(self):
        pass

    def how_libvirt(self):
        pass

    def how_openstack(self):
        pass

    def how_docker(self):
        self.container(self)

    def how_podman(self):
        self.container(self)

    def how_container(self):
        pass

    def how_virtual(self):
        pass


    ## END of API ##
    def add_defaults(self):
        """ Adds default config entries
            1) Disable default sync
            2) To sync plan workdir
        """
        self.add_synced_folder(".", "/vagrant", 'disabled: true')

        dir = self.step.plan.workdir
        self.add_synced_folder(dir, dir)

        self.vf_backup()
        try:
            self.add_raw_config("provider 'libvirt' do |libvirt| libvirt.qemu_use_session = true ; end")
        except:
            self.vf_restore()

        return True

    def run_vagrant_success(self, *args):
        """ Run vagrant command and raise an error if it fails
            see run_vagrant() for args
        """
        self.debug()

        cps = self.run_vagrant(*args)
        if cps.returncode != 0:
            raise ConvertError(f'Failed to run vagrant:{self.eol}\
                  command: {self.hr(args)}{self.eol}\
                  stdout:  {self.hr(cps.stdout)}{self.eol}\
                  stderr:  {self.hr(cps.stderr)}{self.eol}\
                ')
        return cps

    def run_vagrant(self, *args):
        """ Run a Vagrant command

              args = 'command args'

            or

              args = ['comand', 'args']

            return subprocess.CompletedProcess
        """
        self.debug()

        if len(args) == 0:
            raise RuntimeError("vagrant has to run with args")

        cmd = self.prepend(args, self.executable)

        self.debug('command', cmd)

        cps = subprocess.run(
            cmd,
            timeout = self.timeout,
            cwd = self.provision_dir,
            capture_output=True)

        self.debug('stdout', cps.stdout.splitlines())
        self.debug('stderr', cps.stderr.splitlines())
        self.debug('returncode', cps.returncode)

        return cps

    def add_synced_folder(self, sync_from, sync_to, *args):
        return self.add_config('synced_folder',
            self.quote(sync_from),
            self.quote(sync_to),
            f'type: {self.quote(self.sync_type)}', *args)

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

        return self.add_raw_config(config)

    def add_raw_config(self, config):
        """ Add arbitrary config entry into Vagrantfile
            right before last 'end'.
            Prepends with `config_prefix`.
        """
        vfdata = self.vf_read()

        # Lookup last 'end' in Vagrantfile
        i = 0
        for line in reversed(vfdata):
            i -= 1
            if (line.find('end') != -1):
                break

        vfdata = vfdata[:i] \
            + [self.config_prefix + config] \
            + vfdata[i:]

        return self.vf_write(vfdata)

    def vf_read(self):
        return open(self.vagrantfile).read().splitlines()

    def vf_write(self, vfdata):
        if type(vfdata) is list:
            vfdata = self.eol.join(vfdata)

        with open(self.vagrantfile, 'w', newline=self.eol) as f:
            f.write(vfdata)

        self.debug('Vagrantfile', vfdata)
        return self.validate()

    def vf_backup(self):
        """ backup Vagrantfile contents to vf_data """
        self.vf_data = self.vf_read()
        return self.vf_data

    def vf_restore(self):
        """ restore Vagrantfile contents frmo vf_data"""
        return self.vf_write(self.vf_data)


    ## Helpers ##
    def debug(self, key = '', val = '', i = 1):
        """ debugging, yay!
            args: key, value, indent
            all optional
        """
        if self.verbose:
            ind = self.default_indent * i

            if type(val) is list and len(val):
                self.debug(key, '\\', i)
                for v in val:
                    self.debug(' ' * len(key), v, i)
                return

            val = self.hr(val)

            if key.strip() and len(val):
                sep = '='
            else:
                sep = ' '

            echo(' ' * ind + f'{key} {sep} {val}')

    def hr(self, val):
        """ return human readable data """
        if type(val) is tuple or type(val) is list:
            ret = ''
            for v in val:
                ret += self.hr(v)
            return ret

        if type(val) is bytes:
            val = str(val, "utf-8")

        eol = ''
        try:
            val = rstrip(val)
            eol = self.eol

        except:
            pass

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

    def quote(self, string):
        return f'"{string}"'
