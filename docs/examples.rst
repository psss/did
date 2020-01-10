
======================
    Examples
======================

Let's have a look at a couple of real-life examples!

You can obtain detailed list of available options for each command
by invoking it with ``--help``. To control the verbosity of the
output, use ``--debug`` and ``--quiet``. Depending on the command,
``--verbose`` might be also available.

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

Append ``--verbose`` to get the list of source files where
metadata are defined::

    $ tmt show /test/docs --verbose
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

    $ tmt tests ls --condition 'tier > 0'
    /tests/ls


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


Convert Tests
------------------------------------------------------------------

Use ``tmt tests convert`` to gather old metadata stored in
different sources and convert them into the new ``fmf`` format.
By default ``Makefile`` and ``PURPOSE`` files in the current
directory are inspected and the ``Nitrate`` test case management
system is contacted to gather all related metadata::

    makefile ..... summary, component, duration
    purpose ...... description
    nitrate ...... environment, relevancy

In order to fetch data from Nitrate you need to have ``nitrate``
module installed. You can also use ``--no-nitrate`` to disable
Nitrate integration. Use ``--no-makefile`` and ``--no-purpose``
switches to disable the other two metadata sources.

Example output of metadata conversion::

    $ tmt test convert
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

Options ``-f`` or ``--force`` can be used to overwrite existing
files.



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

    $ tmt test run
    /var/tmp/tmt/run-080

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

    /plans/helps
        discover
            how: shell
            directory: /home/psss/git/tmt
            tests: 4 tests selected
        provision
        prepare
        execute
            how: shell
            result: 2 tests passed, 0 tests failed
        report
        finish

    /plans/smoke
        discover
            how: shell
            tests: 0 tests selected
        provision
        prepare
        execute
            how: shell
            result: 1 test passed, 0 tests failed
        report
        finish


Dry run mode is enabled with the ``--dry`` option::

    tmt run --dry



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
