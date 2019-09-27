======================
    Examples
======================

Let's have a look at a couple of real-life examples!

tmt test convert
-----------------

Converting old test metadata into ``fmf`` format is easy::

    tmt test convert

The output looks like this::

    Checking the '/home/psss/git/tmt/examples/convert' directory.
    Makefile found in '/home/psss/git/tmt/examples/convert/Makefile'.
    test: /tmt/smoke
    description: Simple smoke test
    component: tmt
    duration: 5m
    Purpose found in '/home/psss/git/tmt/examples/convert/PURPOSE'.
    description:
    Just run 'tmt --help' to make sure the binary is sane.
    This is really that simple. Nothing more here. Really.
    Nitrate test case found 'TC#0603489'.
    contact: Petr Šplíchal <psplicha@redhat.com>
    environment:
    {'TEXT': 'Text with spaces', 'X': '1', 'Y': '2', 'Z': '3'}
    relevancy:
    distro = rhel-4, rhel-5: False
    distro = rhel-6: False
    Metadata successfully stored into '/home/psss/git/tmt/examples/convert/main.fmf'.

And here's the resulting ``main.fmf`` file::

    component: tmt
    contact: Petr Šplíchal <psplicha@redhat.com>
    description: |
        Just run 'tmt --help' to make sure the binary is sane.
        This is really that simple. Nothing more here. Really.
    duration: 5m
    environment:
        TEXT: Text with spaces
        X: '1'
        Y: '2'
        Z: '3'
    relevancy: |
        distro = rhel-4, rhel-5: False
        distro = rhel-6: False
    summary: Simple smoke test

Give it a try!
