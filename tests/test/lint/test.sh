#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "cp -a data $tmp"
        rlRun "pushd $tmp/data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Perfect"
        rlRun "tmt test lint perfect | tee output"
        rlAssertGrep 'pass' output
        rlAssertGrep 'pass correct attributes are used' output
        rlAssertNotGrep 'warn' output
        rlAssertNotGrep 'fail' output
    rlPhaseEnd

    rlPhaseStartTest "Good"
        rlRun "tmt test lint good | tee output"
        rlAssertGrep 'pass' output
        rlAssertGrep 'warn' output
        rlAssertNotGrep 'fail' output
        rlAssertGrep "Markdown file doesn't exist in the current working
directory." output
        rlAssertGrep "Manual steps couldn't be exported" output
    rlPhaseEnd

    rlPhaseStartTest "Old yaml"
        rlRun "tmt test lint old-yaml | tee output"
        rlAssertGrep 'warn seems to use YAML 1.1' output
    rlPhaseEnd

    rlPhaseStartTest "Bad"
        rlRun "tmt test lint bad | tee output" 1
        rlAssertGrep 'fail test script must be defined' output
        rlRun "tmt test lint bad-path | tee output" 1
        rlAssertGrep 'fail directory path must exist' output
        rlRun "tmt test lint bad-not-absolute | tee output" 1
        rlAssertGrep 'fail directory path must be absolute' output
        rlAssertGrep 'fail directory path must exist' output
        rlRun "tmt test lint relevancy | tee output" 1
        rlAssertGrep 'fail relevancy has been obsoleted' output
        # There should be no change without --fix
        for format in list text; do
            rlAssertGrep 'relevancy' "relevancy-$format.fmf"
            rlAssertNotGrep 'adjust:' "relevancy-$format.fmf"
        done
        rlRun "tmt test lint bad-attribute | tee output" 1
        rlAssertGrep "fail unknown attribute 'requires' is used" output
        rlRun "tmt test lint coverage | tee output" 1
        rlAssertGrep "fail coverage has been obsoleted by link" output
    rlPhaseEnd

    rlPhaseStartTest "Fix"
        # With --fix relevancy should be converted
        rlRun "tmt test lint --fix relevancy | tee output"
        rlAssertGrep 'relevancy converted into adjust' output
        for format in list text; do
            rlAssertNotGrep 'relevancy' "relevancy-$format.fmf"
            rlIsFedora && rlAssertGrep '#comment' "relevancy-$format.fmf"
            rlAssertGrep 'adjust:' "relevancy-$format.fmf"
            rlAssertGrep 'when: distro == rhel' "relevancy-$format.fmf"
        done
    rlPhaseEnd

    rlPhaseStartTest "Manual test"
        # Single Markdown file and it's good
        rlRun "cd manual_test_passed"
        rlRun "tmt test lint good | tee output"
        rlAssertGrep 'pass correct headings are used in the Markdown file' \
          output

        # Many Markdown files
        rlRun "pushd $tmp/data"
        rlRun "cd two_or_more_manual_test"
        rlRun "tmt test lint good | tee output"
        rlAssertGrep "2 Markdown files found in the current working
directory." output

        # Unknown headings
        rlRun "pushd $tmp/data"
        rlRun "cd manual_test_failed"
        rlRun "tmt test lint good | tee output"
        rlAssertGrep "fail unknown html heading \"<h2>Test</h2>\" is
used" output
        rlAssertGrep "fail unknown html heading \"<h3>Unknown heading
begin</h3>\" is used" output
        rlAssertGrep "fail unknown html heading \"<h2>Unknown heading
end</h2>\" is used" output

        # Warn if 2 or more # Setup or # Cleanup are used
        rlAssertGrep 'fail 2 headings "<h1>Setup</h1>" are used' output
        rlAssertGrep 'fail 3 headings "<h1>Cleanup</h1>" are used' output

        # Step is used outside of test sections.
        rlAssertGrep "Heading \"<h2>Step</h2>\" from the section \"Step\" is
used outside of Test sections." output

        # Unexpected headings
        rlAssertGrep "fail Headings \"<h1>Cleanup</h1>, <h1>Setup</h1>\"
aren't expected in the section \"<h1>Test</h1>" output
        rlAssertGrep "fail Headings \"<h1>Cleanup</h1>\" aren't expected in
the section \"<h1>Test two</h1>\"" output

        # Step isn't in pair with Expect
        rlAssertGrep "fail The number of headings from the section \"Step\" - 2
doesn't equal to the number of headings from the section \"Expect\" - 1 in the
test section \"<h1>Test two</h1>\"" output

        # Required section doesn't exist
        rlRun "pushd $tmp/data"
        rlRun "cd manual_test_failed_2"
        rlRun "tmt test lint good | tee output"
        rlAssertGrep "fail \"Test\" section doesn't exist in the Markdown
file" output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
