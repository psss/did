
======================
    Examples
======================

Let's have a look at a couple of real-life examples!

You can obtain detailed list of available options for each command
by invoking it with ``--help``. In order to control the verbosity
of the output use ``--verbose`` and ``--quiet``. To display
implementation details for debugging use the ``--debug`` option.
See :ref:`/stories/cli/common` options for details.

Simply run ``tmt`` to get started with exploring your working
directory::

    $ tmt
    Found 2 tests: /tests/docs and /tests/ls.
    Found 3 plans: /plans/basic, /plans/helps and /plans/smoke.
    Found 109 stories: /spec/core/description, /spec/core/order,
    /spec/core/summary, /spec/plans/artifact, /spec/plans/gate,
    /spec/plans/summary, /spec/steps/discover and 103 more.



Init
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before starting a new project initialize the metadata tree root::

    $ tmt init
    Tree '/tmp/try' initialized.
    To populate it with example content, use --template with mini, base or full.

You can also populate it with a minimal plan example::

    $ tmt init --template mini
    Tree '/tmp/try' initialized.
    Applying template 'mini'.
    Directory '/tmp/try/plans' created.
    Plan '/tmp/try/plans/example.fmf' created.

Create a plan and a test::

    $ tmt init --template base
    Tree '/tmp/try' initialized.
    Applying template 'base'.
    Directory '/tmp/try/tests/example' created.
    Test metadata '/tmp/try/tests/example/main.fmf' created.
    Test script '/tmp/try/tests/example/test.sh' created.
    Directory '/tmp/try/plans' created.
    Plan '/tmp/try/plans/example.fmf' created.

Initialize with a richer example that also includes the story
(overwriting existing files)::

    $ tmt init --template full --force
    Tree '/tmp/try' already exists.
    Applying template 'full'.
    Directory '/tmp/try/tests/example' already exists.
    Test metadata '/tmp/try/tests/example/main.fmf' overwritten.
    Test script '/tmp/try/tests/example/test.sh' overwritten.
    Directory '/tmp/try/plans' already exists.
    Plan '/tmp/try/plans/example.fmf' overwritten.
    Directory '/tmp/try/stories' created.
    Story '/tmp/try/stories/example.fmf' created.



Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``tests`` command is used to investigate and handle tests.
See the :ref:`specification` for details about the L1 Metadata.


Explore Tests
------------------------------------------------------------------

Use ``tmt tests`` to briefly list discovered tests::

    $ tmt tests
    Found 2 tests: /tests/docs and /tests/ls.

Use ``tmt tests ls`` to list available tests, one per line::

    $ tmt tests ls
    /tests/docs
    /tests/ls

Use ``tmt tests show`` to see detailed test metadata::

    $ tmt tests show
    /tests/docs
         summary Check that essential documentation is working
         contact Petr Šplíchal <psplicha@redhat.com>
            test ./test.sh
            path /tests/docs
        duration 5m
            tier 0
          result respect
         enabled yes

    /tests/ls
         summary List available tests and plans
     description Make sure that 'tmt test ls' and 'tmt plan ls' work.
         contact Petr Šplíchal <psplicha@redhat.com>
            test ./test.sh
            path /tests/ls
        duration 5m
            tier 1
          result respect
         enabled yes

Append ``--verbose`` to get additional information about test as
the list of source files where metadata are defined and its full id::

    $ tmt tests show /tests/docs --verbose
    /tests/docs
         summary Check that essential documentation is working
         contact Petr Šplíchal <psplicha@redhat.com>
            test ./test.sh
            path /tests/docs
        duration 5m
            tier 0
          result respect
         enabled yes
         sources /home/psss/git/tmt/tests/main.fmf
                 /home/psss/git/tmt/tests/docs/main.fmf
          fmf-id name: /tests/docs
                 url: https://github.com/psss/tmt.git


Filter Tests
------------------------------------------------------------------

Both ``tmt tests ls`` and ``tmt tests show`` can optionally filter
tests with a regular expression, filter expression or a Python
condition::

    $ tmt tests show docs
    /tests/docs
         summary Check that essential documentation is working
         contact Petr Šplíchal <psplicha@redhat.com>
            test ./test.sh
            path /tests/docs
        duration 5m
            tier 0
          result respect
         enabled yes

    $ tmt tests ls --filter 'tier: 0'
    /tests/docs

    $ tmt tests ls --condition 'int(tier) > 0'
    /tests/ls

In order to select tests under the current working directory use
the single dot notation::

    $ tmt test show .
    $ tmt run test --name .


Lint Tests
------------------------------------------------------------------

Use ``tmt tests lint`` to check defined test metadata against the
L1 Metadata Specification::

    $ tmt tests lint
    /tests/docs
    pass test script must be defined
    pass directory path must be defined
    warn summary should not exceed 50 characters

    /tests/ls
    pass test script must be defined
    pass directory path must be defined


Create Tests
------------------------------------------------------------------

Use ``tmt test create`` to create a new test based on a template::

    $ tmt test create /tests/smoke
    Template (shell or beakerlib): shell
    Directory '/home/psss/git/tmt/tests/smoke' created.
    Test metadata '/home/psss/git/tmt/tests/smoke/main.fmf' created.
    Test script '/home/psss/git/tmt/tests/smoke/test.sh' created.

Specify templates non-interactively with ``-t`` or ``--template``::

    $ tmt tests create --template shell /tests/smoke
    $ tmt tests create --t beakerlib /tests/smoke

Use ``-f`` or ``--force`` option to overwrite existing files.


Import Tests
------------------------------------------------------------------

Use ``tmt tests import`` to gather old metadata stored in
different sources and convert them into the new ``fmf`` format.
By default ``Makefile`` and ``PURPOSE`` files in the current
directory are inspected and the ``Nitrate`` test case management
system is contacted to gather all related metadata.

In order to fetch data from Nitrate you need to have ``nitrate``
module installed. For each test case found in Nitrate separate fmf
file is created with metadata unique to that case. Common metadata
found in all test cases are stored in ``main.fmf``. You can use
``--no-nitrate`` to disable Nitrate integration, ``--no-makefile``
and ``--no-purpose`` switches to disable the other two metadata
sources.

Manual test cases can be imported from Nitrate using the
``--manual`` option. Provide either ``--case ID`` or ``--plan ID``
with the Nitrate test case/plan identifier to select which test
case should be imported or which test plan should be checked for
manual test cases. Directory ``Manual`` will be created in the fmf
root directory and manual test cases will be imported there.

Example output of metadata conversion::

    $ tmt test import
    Checking the '/home/psss/git/tmt/examples/convert' directory.
    Makefile found in '/home/psss/git/tmt/examples/convert/Makefile'.
    task: /tmt/smoke
    summary: Simple smoke test
    test: ./runtest.sh
    contact: Petr Splichal <psplicha@redhat.com>
    component: tmt
    duration: 5m
    require: fmf
    recommend: tmt
    Purpose found in '/home/psss/git/tmt/examples/convert/PURPOSE'.
    description:
    Just run 'tmt --help' to make sure the binary is sane.
    This is really that simple. Nothing more here. Really.
    Nitrate test case found 'TC#0603489'.
    extra-summary: tmt convert test
    contact: Petr Šplíchal <psplicha@redhat.com>
    environment:
    {'TEXT': 'Text with spaces', 'X': '1', 'Y': '2', 'Z': '3'}
    tag: ['NoRHEL4', 'NoRHEL5', 'Tier3']
    tier: 3
    component: tmt
    enabled: True
    relevancy:
    distro = rhel-4, rhel-5: False
    distro = rhel-6: False
    Metadata successfully stored into '/home/psss/git/tmt/examples/convert/main.fmf'.

And here's the resulting ``main.fmf`` file::

    summary: Simple smoke test
    description: |
        Just run 'tmt --help' to make sure the binary is sane.
        This is really that simple. Nothing more here. Really.
    contact: Petr Šplíchal <psplicha@redhat.com>
    component:
    - tmt
    test: ./runtest.sh
    require:
    - fmf
    recommend:
    - tmt
    environment:
        TEXT: Text with spaces
        X: '1'
        Y: '2'
        Z: '3'
    duration: 5m
    enabled: true
    tag:
    - NoRHEL4
    - NoRHEL5
    - Tier3
    tier: '3'
    relevancy: |
        distro = rhel-4, rhel-5: False
        distro = rhel-6: False
    extra-summary: tmt convert test
    extra-task: /tmt/smoke
    extra-nitrate: TC#0603489


Export Tests
------------------------------------------------------------------

Use ``tmt tests export`` command to export test metadata into
different formats and tools. By default all available tests are
exported, specify regular expression matching test name to export
only selected tests or use ``.`` to export tests under the current
directory::

    $ tmt tests export --nitrate .
    Test case 'TC#0603489' found.
    summary: tmt convert test
    script: /tmt/smoke
    components: tmt
    tags: NoRHEL4 Tier3 NoRHEL5 fmf-export
    default tester: psplicha@redhat.com
    estimated time: 5m
    status: CONFIRMED
    arguments: TEXT='Text with spaces' X=1 Y=2 Z=3
    Structured Field:
    relevancy: distro = rhel-4, rhel-5: False
    distro = rhel-6: False
    description: Simple smoke test
    purpose-file: Just run 'tmt --help' to make sure the binary is sane.
    This is really that simple. Nothing more here. Really.
    fmf id:
    name: /
    path: /examples/convert
    url: https://github.com/psss/tmt.git
    Test case 'TC#0603489' successfully exported to nitrate.


Test Libraries
------------------------------------------------------------------

In order to prevent unnecessary test code duplication it makes
sense to use a test library which implements frequently repeated
actions. Currently beakerlib libraries are supported. They can be
defined in the :ref:`/spec/tests/require` attribute and are
fetched during the :ref:`/spec/steps/discover` step.

Use the short backward-compatible syntax to fetch libraries from
the `default repository`__::

    require: library(openssl/certgen)

__ https://github.com/beakerlib/

The full fmf identifier allows to fetch libraries from arbitrary
location::

    require:
        - url: https://github.com/beakerlib/openssl
          name: /certgen

See the :ref:`/spec/tests/require` attribute specification for
detailed description of the syntax and available keys.



Plans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``plans`` command is used to investigate and handle plans.
See the :ref:`specification` for details about the L2 Metadata.


Explore Plans
------------------------------------------------------------------

Exploring ``plans`` is similar to using ``tests``::

    $ tmt plans
    Found 3 plans: /plans/basic, /plans/helps and /plans/smoke.

Use ``tmt plans ls`` and ``tmt plans show`` to output plan names
and detailed plan information, respectively::

    $ tmt plans ls
    /plans/basic
    /plans/helps
    /plans/smoke

    $ tmt plans show
    /plans/basic
         summary Essential command line features
        discover
             how fmf
      repository https://github.com/psss/tmt
        revision devel
          filter tier: 0,1
         prepare
             how ansible
       playbooks plans/packages.yml

    /plans/helps
         summary Check help messages
        discover
             how shell

    /plans/smoke
         summary Just a basic smoke test
         execute
             how shell
          script tmt --help

Verbose output and filtering are similar as for exploring tests.
See `Explore Tests`_ and `Filter Tests`_ for more examples.


Create Plans
------------------------------------------------------------------

Use ``tmt plan create`` to create a new plan with templates::

    tmt plans create --template mini /plans/smoke
    tmt plans create --t full /plans/features

In order to override default template content directly from the
command line use individual step options and provide desired data
in the ``yaml`` format::

    tmt plan create /plans/custom --template mini \
        --discover '{how: "fmf", name: "internal", url: "https://internal/repo"}' \
        --discover '{how: "fmf", name: "external", url: "https://external/repo"}'

Options ``-f`` or ``--force`` can be used to overwrite existing
files.


Inherit Plans
------------------------------------------------------------------

If several plans share similar content it is possible to use
inheritance to prevent unnecessary duplication of the data::

    discover:
        how: fmf
        repository: https://github.com/psss/tmt
    prepare:
        how: ansible
        playbooks: ansible/packages.yml
    execute:
        how: beakerlib

    /basic:
        summary: Quick set of basic functionality tests
        discover+:
            filter: tier:1

    /features:
        summary: Detailed tests for individual features
        discover+:
            filter: tier:2

Note that a ``+`` sign should be used if you want to extend the
parent data instead of replacing them. See the `fmf features`_
documentation for a detailed description of the hierarchy,
inheritance and merging attributes.

.. _fmf features: https://fmf.readthedocs.io/en/latest/features.html


Multiple Configs
------------------------------------------------------------------

Step can contain multiple configurations. In this case provide
each config with a unique name. Applying ansible playbook and
executing custom script in a single :ref:`/spec/steps/prepare`
step could look like this::

    prepare:
      - name: packages
        how: ansible
        playbooks: plans/packages.yml
      - name: services
        how: shell
        script: systemctl start service

Another common use case which can be easily covered by multiple
configs can be fetching tests from multiple repositories during
the :ref:`/spec/steps/discover` step::

    discover:
      - name: upstream
        how: fmf
        repository: https://github.com/psss/tmt
      - name: fedora
        how: fmf
        repository: https://src.fedoraproject.org/rpms/tmt/


Extend Steps
------------------------------------------------------------------

When defining multiple configurations for a step it is also
possible to make use of fmf inheritance. For example the common
preparation config can be defined up in the hierarchy::

    prepare:
      - name: tmt
        how: install
        package: tmt

Extending the prepare config in a child plan to install additional
package then could be done in the following way::

    prepare+:
      - name: pytest
        how: install
        package:
            - python3-pytest
            - python3-mock


Stories
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``stories`` command is used to investigate and handle stories.
See the :ref:`specification` for details about the L3 Metadata.


Explore Stories
------------------------------------------------------------------

Exploring ``stories`` is quite similar to using ``tests`` or
``plans``::

    $ tmt stories
    Found 109 stories: /spec/core/description, /spec/core/order,
    /spec/core/summary, /spec/plans/artifact, /spec/plans/gate,
    /spec/plans/summary, /spec/steps/discover and 102 more.

The ``tmt stories ls`` and ``tmt stories show`` commands output
the names and the detailed information, respectively::

    $ tmt stories ls
    /spec/core/description
    /spec/core/order
    /spec/core/summary
    ...

    $ tmt stories show
    /spec/core/description
         summary Detailed description of the object
           story I want to have common core attributes used consistently
                 across all metadata levels.
     description Multiline ``string`` describing all important aspects of
                 the object. Usually spans across several paragraphs. For
                 detailed examples using a dedicated attributes 'examples'
                 should be considered.
     ...

Verbose output and filtering are similar as for exploring tests.
See `Explore Tests`_ and `Filter Tests`_ for more examples.


Filter Stories
------------------------------------------------------------------

Additionally, and specifically to stories, special flags are
available for binary status filtering::

    $ tmt stories show --help | grep only
      -i, --implemented    Implemented stories only.
      -I, --unimplemented  Unimplemented stories only.
      -t, --tested         Tested stories only.
      -T, --untested       Untested stories only.
      -d, --documented     Documented stories only.
      -D, --undocumented   Undocumented stories only.
      -c, --covered        Covered stories only.
      -C, --uncovered      Uncovered stories only.

    $ tmt stories ls --implemented
    /spec/core/summary
    /stories/api/plan/attributes/artifact
    /stories/api/plan/attributes/gate
    ...

    $ tmt stories show --documented
    /stories/cli/common/debug
         summary Print out everything tmt is doing
           story I want to have common command line options consistenly used
                 across all supported commands and subcommands.
         example tmt run -d
                 tmt run --debug
     implemented /tmt/cli
      documented /tmt/cli
    ...

In order to select stories under the current working directory use
the single dot notation::

    $ tmt story show .


Story Coverage
------------------------------------------------------------------

Current status of the code, test and documentation coverage can be
checked using the ``tmt story coverage`` command::

    $ tmt story coverage
    code test docs story
    todo todo todo /spec/core/description
    todo todo todo /spec/core/order
    done todo todo /spec/core/summary
    ...
    done todo todo /stories/cli/usability/completion
     39%   9%   9% from 109 stories


Create Stories
------------------------------------------------------------------

The ``tmt story create`` command can be used to create a new story
based on given template::

    tmt story create --template full /stories/usability

Use ``-f`` or ``--force`` to overwrite existing files.



Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``tmt run`` command is used to execute tests. By default all
steps for all discovered test plans are executed::

    $ tmt run
    /var/tmp/tmt/run-581

    /plans/basic
        discover
            how: fmf
            directory: /home/psss/git/tmt
            filter: tier: 0,1,2
            summary: 15 tests selected
        provision
            how: local
            distro: Fedora release 32 (Thirty Two)
            summary: 1 guest provisioned
        prepare
            how: ansible
            playbook: ansible/packages.yml
            how: install
            summary: Install required packages
            package: beakerlib
            summary: 2 preparations applied
        execute
            how: beakerlib
            summary: 15 tests executed
        report
            how: display
            summary: 15 tests passed
        finish
            summary: 0 tasks completed

Even if there are no :ref:`/spec/plans` defined it is still
possible to execute tests and custom scripts. See the default
:ref:`/stories/cli/run/default/plan` story for details. For
example, in order to run beakerlib tests you could do this::

    tmt run -a execute -h beakerlib

Dry run mode is enabled with the ``--dry`` option::

    tmt run --dry

Each test run creates a workdir where relevant data such as tests
code from the discover step or test results from the execute step
are stored. If you don't need to investigate test logs and other
artifacts generated by the run you can remove the workdir after
the execution is finished::

    tmt run --remove
    tmt run --rm
    tmt run -r


Select Plans
------------------------------------------------------------------

Choose which plans should be executed::

    $ tmt run plan --name basic
    /var/tmp/tmt/run-083

    /plans/basic
        discover
            how: fmf
            repository: https://github.com/psss/tmt
            revision: devel
            filter: tier: 0,1
            tests: 2 tests selected
        provision
        prepare
        execute
            how: beakerlib
            result: 2 tests passed, 0 tests failed
        report
        finish


Select Tests
------------------------------------------------------------------

Run only a subset of available tests across all plans::

    $ tmt run test --filter tier:1
    /plans/basic
        discover
            how: fmf
            repository: https://github.com/psss/tmt
            revision: devel
            filter: tier: 0,1
            tests: 1 test selected
        ...

    /plans/helps
        discover
            how: shell
            directory: /home/psss/git/tmt
            tests: 0 tests selected
        ...

    /plans/smoke
        discover
            how: shell
            tests: 0 tests selected
        ...


Select Steps
------------------------------------------------------------------

The test execution is divided into the following six steps:
``discover``, ``provision``, ``prepare``, ``execute``, ``report``
and ``finish``. See the :ref:`specification` for more details
about individual steps.

It is possible to execute only selected steps. For example in
order to see which tests would be executed without actually
running them choose the ``discover`` step::

    $ tmt run discover
    /var/tmp/tmt/run-085

    /plans/basic
        discover
            how: fmf
            repository: https://github.com/psss/tmt
            revision: devel
            filter: tier: 0,1
            tests: 2 tests selected

    /plans/helps
        discover
            how: shell
            directory: /home/psss/git/tmt
            tests: 4 tests selected

Use ``--verbose`` and ``--debug`` to enable more detailed output
such as list of individual tests or showing the progress of the
test environment provisioning::

    $ tmt run discover --verbose
    /var/tmp/tmt/run-767

    /plans/basic
        discover
            how: fmf
            repository: https://github.com/psss/tmt
            revision: devel
            filter: tier: 0,1
            tests: 2 tests selected
                /one/tests/docs
                /one/tests/ls

    /plans/helps
        discover
            how: shell
            directory: /home/psss/git/tmt
            tests: 4 tests selected
                /help/main
                /help/test
                /help/plan
                /help/smoke

You can also choose multiple steps to be executed::

    tmt run discover provision prepare

Arguments for particular step can be specified after the step
name, options for all steps should go to the ``run`` command::

    tmt run discover provision --debug  # debug output for provision only
    tmt run --debug discover provision  # debug output for all steps

In order to execute all test steps while providing arguments to
some of them it is possible to use the ``--all`` option::

    tmt run --all provision --how=local


Provision Options
------------------------------------------------------------------

By default, tests are executed under a virtual machine so that
your laptop is not affected by unexpected changes. The following
commands are equivalent::

    tmt run
    tmt run -a provision -h virtual
    tmt run --all provision --how=virtual

You can also use an alternative virtual machine implementation
using the ``testcloud`` provisioner::

    tmt run --all provision --how=virtual.testcloud

If you already have a box ready for testing with ``ssh`` enabled,
use the ``connect`` method::

    tmt run --all provision --how=connect --guest=name-or-ip --user=login --password=secret
    tmt run --all provision --how=connect --guest=name-or-ip --key=private-key-path

The ``container`` method allows to execute tests in a container
using ``podman``::

    tmt run --all provision --how=container --image=fedora:latest

If you are confident that tests are safe you can execute them
directly on your ``local`` host::

    tmt run --all provision --how=local


Debug Tests
------------------------------------------------------------------

For debugging tests, the execution is anticipated to be split into
separate invocations for provisioning, repeatedly (re)executing
the test and cleaning up::

    tmt run --id <ID> --until provision  # prepare the testing environment

    tmt run -i <ID> execute              # ... and update the test
    tmt run -i <ID> execute              # ... and update the test again
    tmt run -i <ID> execute              # ... until you're done

    tmt run -i <ID> report finish

Instead of always specifying the whole run id you can also use
``--last`` or ``-l`` as an abbreviation for the last run id::

    tmt run -l execute
    tmt run --last execute

In order to interactively debug tests use the ``--interactive``
option which disables output capturing so that you can see what
exactly is happening during test execution. This also allows to
inspect particular place of the code by inserting a ``bash`` in
the shell code or ``import pdb; pdb.set_trace()`` for python::

    tmt run --all execute --how tmt --interactive


Aliases
------------------------------------------------------------------

It might be useful to set up a set of shell aliases for the tmt
command lines which you often use. For a quick reservation of
a machine or a container for quick experimenting::

    alias reserve='tmt run login --step execute execute finish provision --how container --image fedora'

Reserving a testing box then can be as short as this::

    reserve
    reserve -h virtual
    reserve -i fedora:32
    reserve --how virtual
    reserve --image fedora:32

For interactive debugging of tests the following three aliases can
come in handy::

    alias start='tmt run --verbose --until report execute --how tmt --interactive test --name . provision --how virtual --image fedora'
    alias retest='tmt run --last test --name . discover -f execute -f --how tmt --interactive'
    alias stop='tmt run --last report --verbose finish'

The test debugging session then can look like this::

    start
    retest
    retest
    retest login
    ...
    stop

First you ``start`` the session in order to provision a testing
environment, then you ``retest`` your test code changes as many
times as you need to finalize the test implementation, and finally
``stop`` is used to clean up the testing environment.


Guest Login
------------------------------------------------------------------

Use the ``login`` command to get an interactive shell on the
provisined guest. This can be useful for example for additional
manual preparation of the guest before testing or checking test
logs to investigate a test failure::

    tmt run login --step prepare
    tmt run login --step execute

It's possible to log in at the start or end of a step or select
the desired step phase using order::

    tmt run login --step prepare:start
    tmt run login --step prepare:50
    tmt run login --step prepare:end

Interactive shell session can be also enabled conditionally when
specific test result occurs::

    tmt run login --when fail
    tmt run login --when fail --when error

You can also enable only the ``provision`` step to easily get a
clean and safe environment for experimenting. Use the ``finish``
step to remove provisioned guest::

    tmt run provision login
    tmt run --last finish

Clean up the box right after your are done with experimenting by
combining the above-mentioned commands on a single line::

    tmt run provision login finish

Have you heard already that using command abbreviation is possible
as well? It might save you some typing::

    tmt run pro log fin

See the :ref:`/stories/cli/run/login` user stories for more
details and examples.
