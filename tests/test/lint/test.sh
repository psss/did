#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "cp -a data $tmp"
        rlRun "cp -a data_sources $tmp"
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
    rlPhaseEnd

    rlPhaseStartTest "Old yaml"
        if rlRun "tmt test lint old-yaml 2>&1 | tee output" 0,2; then
            # Before fmf-1.0 we give just a warning
            rlAssertGrep "warn: /old-yaml:enabled - 'yes' is not of type 'boolean'" output
        else
            # Since fmf-1.0 old format is no more supported
            rlAssertGrep 'Invalid.*enabled.*in test' output
        fi
    rlPhaseEnd

    rlPhaseStartTest "Bad"
        rlRun "tmt test lint empty 2>&1 | tee output" 2
        rlAssertGrep "must be defined" output
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
        # Correct syntax
        rlRun "tmt test lint /manual_true/correct_path/pass | tee output"
        rlAssertGrep 'pass correct manual test syntax' output

        # Wrong test path
        rlRun "tmt test lint /manual/manual_true/wrong_path | tee output" 1
        rlAssertGrep "fail file 'wrong_path.md' does not exist" output

        # If manual=false - don't check test attribute
        rlRun "tmt test lint /manual/manual_false | tee output"
        rlAssertNotGrep 'pass correct manual test syntax' output

        # Unknown headings
        rlRun "tmt test lint /manual_true/correct_path/fail1 | tee output" 1
        fail="fail unknown html heading"
        rlAssertGrep "$fail \"<h2>Test</h2>\" is used" output
        rlAssertGrep "$fail \"<h3>Unknown heading begin</h3>\" is used" output
        rlAssertGrep "$fail \"<h2>Unknown heading end</h2>\" is used" output

        # Warn if 2 or more # Setup or # Cleanup are used
        rlAssertGrep 'fail 2 headings "<h1>Setup</h1>" are used' output
        rlAssertGrep 'fail 3 headings "<h1>Cleanup</h1>" are used' output

        # Step is used outside of test sections.
        rlAssertGrep "outside of Test sections" output

        # Unexpected headings
        rlAssertGrep "fail Headings .* aren't expected in the section" output

        # Step isn't in pair with Expect
        rlAssertGrep "doesn't equal to the number of headings" output

        # Required section doesn't exist
        rlRun "tmt test lint /manual_true/correct_path/fail2 | tee output" 1
        rlAssertGrep "fail \"Test\" section doesn't exist" output
    rlPhaseEnd

    rlPhaseStartTest "Lint by modified source files"
        rlRun "pushd $tmp/data_sources"

        lint_cmd="tmt test lint --source"

        # main.fmf is used by all but '/foo/special'
        rlRun -s "$lint_cmd main.fmf"
        for t in /virtual /baz/bb /foo/inner /foobar; do
            rlAssertGrep "$t" "$rlRun_LOG"
        done
        rlAssertNotGrep '/foo/special' "$rlRun_LOG"

        # foo/main.fmf is used single test
        rlRun -s "$lint_cmd $(realpath foo/main.fmf)"
        rlAssertGrep "/foo/inner" "$rlRun_LOG"
        for t in /virtual /baz/bb /foo/special /foobar; do
            rlAssertNotGrep "$t" "$rlRun_LOG"
        done

        # '.' as local directory with single file and a explicit one
        rlRun "pushd foobar"
        rlRun -s "$lint_cmd *.fmf $(realpath ../baz/bb.fmf)"
        rlAssertGrep "/foobar" "$rlRun_LOG"
        rlAssertGrep "/baz/bb" "$rlRun_LOG"
        for t in /virtual /foo/special /foo/special; do
            rlAssertNotGrep "$t" "$rlRun_LOG"
        done
        # From data_sources/foobar
        rlRun "popd"
        # From data_sources
        rlRun "popd"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd" # From data
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
