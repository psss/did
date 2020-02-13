======================
    Questions
======================


Fedora 30
------------------------------------------------------------------

If you want to run tests in virtual machine on Fedora 30 do not
install ``tmt-all`` package. Install base ``tmt`` package instead
and use the following commands to install necessary dependencies::

    dnf install -y vagrant --setopt=install_weak_deps=False
    dnf install -y rubygem-{formatador,excon,builder,ruby-libvirt,nokogiri,multi_json}

Then everything should work fine.


vagrant-rsync-back
------------------------------------------------------------------

If you see an error when installing the ``vagrant-rsync-back``
plugin on Fedora, the following might help::

    sudo dnf remove vagrant-libvirt rubygem-fog-core
    vagrant plugin install vagrant-libvirt

Note that the vagrant plugin installation should be done under
a regular user.
