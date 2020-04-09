======================
    Questions
======================


Fedora 30
------------------------------------------------------------------

If you want to run tests in virtual machine on Fedora 30 do not
install ``tmt-all`` package. Install base ``tmt`` package instead
and use the following commands to install necessary dependencies::

    dnf install -y vagrant libvirt rsync --setopt=install_weak_deps=False
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


Nitrate Migration
------------------------------------------------------------------

After a nitrate test case is migrated to ``fmf`` git becomes the
canonical source of the test case metadata. All further changes
should be done in git and updates synchronized back to nitrate
using ``tmt test export . --nitrate`` command. Otherwise direct
changes in Nitrate might be lost.

A unique identifier of the new test metadata location is stored in
the ``[fmf]`` section of test case notes. Below is the list of
attributes which are synchronized to corresponding nitrate fields:

* component — components tab
* contact — default tester
* description — purpose-file in the structured field
* duration — estimated time
* enabled — status
* environment — arguments
* relevancy — relevancy in the structured field
* summary — description in the structured field
* tag — tags tab
* tier — tags (e.g. ``1`` synced to the ``Tier1`` tag)

The following attributes, if present, are exported as well:

* extra-hardware — hardware in the structured field
* extra-pepa — pepa in the structured field
* extra-summary — Nitrate test case summary
* extra-task — Nitrate test case script

They have the ``extra`` prefix as they are not part of the L1
Metadata Specification and are supposed to be synced temporarily
to keep backward compatibility.
