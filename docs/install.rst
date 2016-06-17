
===============
    Install
===============

Fedora
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Fedora simply install the package::

    dnf install did

That's it! :-)


Copr
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set up the `did repository`__ and install the tool using dnf::

    dnf copr enable psss/did
    dnf install did

This will bring dependencies for all core plugins as well.

__ https://copr.fedoraproject.org/coprs/psss/did/


PIP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Basic dependencies for buiding/installing pip packages::

    sudo yum install gcc krb5-devel
    sudo yum install python-devel python-pip python-virtualenv

Upgrade to the latest pip/setup/virtualenv installer code::

    sudo pip install --upgrade pip setuptools virtualenv

Install into a python virtual environment (OPTIONAL)::

    virtualenv ~/did
    source ~/did/bin/activate

Install did (sudo required if not in a virtualenv)::

    pip install did

See the `pypi package index`__ for detailed package information.

__ https://pypi.python.org/pypi/did


Docker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Please note: This is a first cut at doing a container version as a
result; known issues:

* Kerberos auth may not be working correctly
* Container runs as privileged to access the conf file
* Output directory may not be quite right

This does not actually run the docker image as it makes more sense
to run it directly. Use::

    docker run --privileged --rm -it -v $(HOME)/.did:/did.conf $(USERNAME)/did

If you want to add it to your .bashrc use this::

    alias did="docker run --privileged --rm -it -v $(HOME)/.did:/did.conf $(USERNAME)/did"

A couple of useful resources to get started with docker:

* https://fedoraproject.org/wiki/Docker
* https://fedoraproject.org/wiki/Getting_started_with_docker
