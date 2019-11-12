======================
    Commands
======================

Detailed documentation for individual ``tmt`` subcommands.

--------------------------
        Common information
--------------------------

You can obtain more detailed info for each subcommand by invoking it with
``--help``.
To control the verbosity of the output, use ``--debug`` and ``--quiet``.
Depending on the subcommand, ``--verbose`` might be also available.


--------------------------
        Bare invocation
--------------------------

``tmt`` should get you started with exploring your working directory::

    $ tmt
    Found 2 tests: /tests/docs and /tests/ls.
    Found 3 plans: /plans/basic, /plans/helps and /plans/smoke.
    Found 109 stories: /spec/core/description, /spec/core/order, /spec/core/summary, /spec/plans/artifact, /spec/plans/gate, /spec/plans/summary, /spec/steps/discover, /spec/steps/execute/isolate, /spec/steps/execute/shell/default, /spec/steps/execute/shell/multi, /spec/steps/execute/shell/script, /spec/steps/finish and 97 more.



--------------------------
        tests
--------------------------

``tests`` subcommand is used to investigate and handle test metadata.


Exploring tests (``tmt tests / tmt tests ls / tmt tests show``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``tmt tests`` briefly lists discovered tests::

    $ tmt
    Found 2 tests: /tests/docs and /tests/ls.

.. _subcmd-tests-ls:

``tmt tests ls`` lists available tests, one per line::

    $ tmt tests ls
    /tests/docs
    /tests/ls

.. _subcmd-tests-show:

``tmt tests show`` outputs detailed test metadata::

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

.. _show-verbose:

It gets even more detailed with ``--verbose``::

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
         sources /home/asosedki/code/tmt/tests/main.fmf
                 /home/asosedki/code/tmt/tests/docs/main.fmf


.. _ls-show-filtering:

Both ``tmt tests ls`` and ``tmt tests show`` can optionally filter tests
with a regex, filter expression or a Python condition::

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

    $ tmt tests ls --condition 'tier: 0'
    /tests/docs


.. _subcmd-tests-lint:

Linting tests (``tmt tests lint``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``tmt tests lint``
to run an automated check against the test metadata::

    $ tmt tests lint
    /tests/docs
    pass test script must be defined
    pass directory path must be defined

    /tests/ls
    pass test script must be defined
    pass directory path must be defined


.. _subcmd-tests-create:

Creating tests (``tmt tests create``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``tmt tests create`` to initialize tests with templates::

    $ tmt tests create /tests/smoke
    Template (shell or beakerlib): shell
    Test metadata '/home/asosedki/code/tmt/playground/tests/smoke/main.fmf' created.
    Test script '/home/asosedki/code/tmt/playground/tests/smoke/test.sh' created.

Specify templates non-interactively with ``-t`` / ``--template``::

    $ tmt tests create --template shell /tests/smoke
    $ tmt tests create --t beakerlib /tests/smoke

Use ``-f`` / ``--force`` to overwrite existing files.

One can also opt for a potentially smoother sounding ``test create``.


.. _subcmd-tests-convert:

Converting tests (``tmt tests convert``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``tmt tests convert`` to gather old metadata stored in different
sources and convert them into the new ``fmf`` format.

By default ``Makefile`` and ``PURPOSE`` files in the current
directory are inspected and the ``Nitrate`` test case management
system is contacted to gather all related metadata::

    makefile ..... summary, component, duration
    purpose ...... description
    nitrate ...... environment, relevancy

In order to fetch data from Nitrate you need to have ``nitrate``
module installed. You can also use ``--no-nitrate`` to disable
Nitrate integration.

``--no-makefile`` and ``--no-purpose`` switches
can be used to disable the other two metadata sources.



--------------------------
        plans
--------------------------

Using ``plans`` is similar to using ``tests``::

    $ tmt plans
    Found 3 plans: /plans/basic, /plans/helps and /plans/smoke.

Exploring plans (``tmt plans / tmt plans ls / tmt plans show``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _subcmd-plans-ls:
.. _subcmd-plans-show:

``tmt plans ls`` and ``tmt plans show`` output
the names and the detailed information, respectively::

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

`Verbose output` and `regex/simple/expression filtering` are also available.

.. _Verbose output: show-verbose_
.. _regex/simple/expression filtering: ls-show-filtering_


.. _subcmd-plans-create:

Creating plans (``tmt plans create``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``tmt plans create`` to initialize plans with templates::

    $ tmt plans create --template mini /plans/smoke
    $ tmt plans create --t full /plans/features

Use ``-f`` / ``--force`` to overwrite existing files.

One can also opt for a potentially smoother sounding ``plan create``.



--------------------------
        stories
--------------------------

Using ``stories`` is, once again, quite similar to
using ``tests`` or ``plans``::

    $ tmt stories
    Found 109 stories: /spec/core/description, /spec/core/order, /spec/core/summary, /spec/plans/artifact, /spec/plans/gate, /spec/plans/summary, /spec/steps/discover, /spec/steps/execute/isolate, /spec/steps/execute/shell/default, /spec/steps/execute/shell/multi, /spec/steps/execute/shell/script, /spec/steps/finish and 97 more.


Exploring stories (``tmt stories / tmt stories ls / tmt stories show``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. _subcmd-stories-ls:
.. _subcmd-stories-show:

``tmt stories ls`` and ``tmt stories show`` output
the names and the detailed information, respectively::

    $ tmt stories ls
    /spec/core/description
    /spec/core/order
    --- 8< --- 107 more lines omitted for brewity --- >8 ---

    $ tmt stories show
        /spec/core/description
         summary Detailed description of the object
           story I want to have common core attributes used consistently
                 across all metadata levels.
     description Multiline ``string`` describing all important aspects of
                 the object. Usually spans across several paragraphs. For
                 detailed examples using a dedicated attributes 'examples'
                 should be considered.
    --- 8< --- 1039 more lines omitted for brewity --- >8 ---

`Verbose output` and regex/simple/expression `filtering` are also available.

.. _Verbose output: show-verbose_
.. _filtering: ls-show-filtering_

.. _status-filtering

Additionally, and specifically to stories,
special flags are available for binary status filtering::

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
    --- 8< --- 40 more lines omitted for brewity --- >8 ---

    $ tmt stories show --documented
        /stories/cli/common/debug
         summary Print out everything tmt is doing
           story I want to have common command line options consistenly used
                 across all supported commands and subcommands.
         example tmt run -d
                 tmt run --debug
     implemented /tmt/cli
      documented /tmt/cli
    --- 8< --- 79 more lines omitted for brewity --- >8 ---


.. _subcmd-stories-coverage:

Coverage (``tmt stories coverage``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Statistics for the aforementioned statuses could be obtained with
``tmt stories coverage``::

    $ tmt stories coverage
    code test docs story
    todo todo todo /spec/core/description
    todo todo todo /spec/core/order
    done todo todo /spec/core/summary
    --- 8< --- 104 more lines omitted for brewity --- >8 ---
    done todo todo /stories/cli/usability/completion
     39%   9%   9% from 109 stories

`Regex/simple/expression` and `status filtering` are available.

    $ tmt stories coverage --covered
    code test docs story
    done done done /stories/cli/test/convert
    done done done /stories/cli/test/ls
    100% 100% 100% from 2 stories

.. _Regex/simple/expression filtering: ls-show-filtering_
.. _status filtering: status-filtering_


.. _subcmd-stories-create:

Creating stories (``tmt stories create``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``tmt stories create`` to initialize stories with templates::

    $ tmt stories create --t full /stories/usability

Use ``-f`` / ``--force`` to overwrite existing files.

One can also opt for a potentially smoother sounding ``story create``.



--------------------------
        run
--------------------------

Basic execution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute all steps for all available test plans::

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
            directory: /home/asosedki/code/tmt
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


Dry-run mode is enabled with ``--dry``::

    $ tmt run --dry



Filtering
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filter selected plans/tests::

    $ tmt run plan --name basic   # regex filtering by name
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


    $ tmt run test --filter tier:1  # selects Tier1 tests across all plans
    /plans/basic
        discover
            how: fmf
            repository: https://github.com/psss/tmt
            revision: devel
            filter: tier: 0,1
            tests: 1 test selected
        provision
        prepare
        execute
            how: beakerlib
            result: 1 tests passed, 0 test failed
        report
        finish

    /plans/helps
        discover
            how: shell
            directory: /home/asosedki/code/tmt
            tests: 0 tests selected
        provision
        prepare
        execute
            how: shell
            result: 1 test passed, 0 tests failed
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


Controlling individual steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To execute the selection without running the tests,
limit `tmt run` to the `discovery` step::

    $ tmt run discovery
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
            directory: /home/asosedki/code/tmt
            tests: 4 tests selected

    /plans/smoke
        discover
            how: shell
            tests: 0 tests selected

More detailed output can be obtained
with ``--verbose`` and ``--debug`` switches.


``run`` consists of several steps, these are:
``discover``, ``provision``, ``prepare``,
``execute``, ``report`` and ``finish``.

One can limit ``run`` to only several such steps::

    $ tmt run discover provision prepare

Arguments for particular steps can be specified after the step names,
arguments that affect them all should preceed them::

    $ tmt run --debug discover provision  # debug output for all steps

    $ tmt run discover provision --debug  # debug output for provision only

To provide arguments for particular steps and avoid listing them all,
use ``--all-steps`` followed by the individual step names,
followed, in turn, by their respective arguments::

    $ tmt run --all provision --how=local


Debugging workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For debugging tests, the execution is anticipated to be split into
separate invocations for provisioning,
repeatedly (re)executing the test and cleaning up::

    $ tmt run --id <ID> --until provision  # prepare the testing environment

    $ tmt run -i <ID> execute              # ... and update the test
    $ tmt run -i <ID> execute              # ... and update the test again
    $ tmt run -i <ID> execute              # ... until you're done

    $ tmt run -i <ID> report finish



--------------------------
        init
--------------------------

Initialize the current directory with a default metadata template::

    $ tmt init

Populate it with the minimal plan example instead::

    $ tmt init --mini

Create a plan and a test::

    $ tmt init --base

Initialize with a richer example that also includes the story
(overwriting existing files)::

    $ tmt init --full --force
