
===============
    Install
===============

Copr
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download Copr repository from the project page:

* https://copr.fedoraproject.org/coprs/psss/status-report/

Install using yum::

    yum install status-report

or dnf::

    dnf install status-report

This will bring dependencies for all core plugins as well.


PIP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Basic dependencies for buiding/installing pip packages::

    sudo yum install gcc krb5-devel
    sudo yum install python-devel python-pip python-virtualenv

Upgrade to the latest pip/setup/virtualenv installer code::

    sudo pip install -U pip setuptools virtualenv

Install into a python virtual environment (OPTIONAL)::

    virtualenv --no-site-packages ~/virtenv_statusreport
    source ~/virtenv_statusreport/bin/activate

Install status_report (sudo required if not in a virtualenv)::

    pip install status_report


Docker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Please note: This is a first cut at doing a container version as a
result; known issues:

* Kerberos auth may not be working correctly
* Container runs as privileged to access the conf file
* Output directory may not be quite right

This does not actually run the docker image as it makes more sense
to run it directly. Use::

    docker run --privileged --rm -it -v $(HOME)/.status-report:/status-report.conf $(USERNAME)/status-report

If you want to add it to your .bashrc use this::

    alias status-report="docker run --privileged --rm -it -v $(HOME)/.status-report:/status-report.conf $(USERNAME)/status-report"

A couple of useful resources to get started with docker:

* https://fedoraproject.org/wiki/Docker
* https://fedoraproject.org/wiki/Getting_started_with_docker
