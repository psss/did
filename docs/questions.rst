======================
    Questions
======================



Installing the 'vagrant-rsync-back' plugin
------------------------------------------

If you see an error when installing the ``vagrant-rsync-back``
plugin on Fedora, the following might help::

    sudo dnf remove vagrant-libvirt rubygem-fog-core
    vagrant plugin install vagrant-libvirt

Note that the vagrant plugin installation should be done under
a regular user.
