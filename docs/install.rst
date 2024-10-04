
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

Installing did using pip directly on the system is easy::

    pip install did

Use virtual environments if you do not want to affect your system.
Install virtualenv wrapper to make the work more comfortable::

    sudo dnf install python-virtualenvwrapper   # Fedora
    sudo apt install virtualenvwrapper          # Ubuntu

Create a new virtual environment, upgrade tools, install did::

    mkvirtualenv did
    workon did
    pip install --upgrade pip setuptools
    pip install did

This installs the tool and basic requirements. Some of the plugins
have additional dependencies. Use ``did[plugin]`` to install extra
dependencies, for example::

    pip install did[bugzilla]   # Install bugzilla deps
    pip install did[docs]       # Get everything for building docs
    pip install did[tests]      # And for testing
    pip install did[all]        # Install all extra dependencies

Note: For plugins depending on gssapi (jira & rt) there are some
extra dependencies::

    sudo dnf install gcc krb5-devel python-devel    # Fedora
    sudo apt install gcc libkrb5-dev python-dev     # Ubuntu

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
