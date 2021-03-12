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
        rlAssertNotGrep 'warn' output
        rlAssertNotGrep 'fail' output
    rlPhaseEnd

    rlPhaseStartTest "Good"
        rlRun "tmt test lint good | tee output"
        rlAssertGrep 'pass' output
        rlAssertGrep 'warn' output
        rlAssertNotGrep 'fail' output
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
        rlAssertGrep "fail Unknown attribute 'requires' is used" output
    rlPhaseEnd

    rlPhaseStartTest "Fix"
        # With --fix relevancy should be converted
        rlRun "tmt test lint --fix relevancy | tee output"
        rlAssertGrep 'relevancy converted into adjust' output
        for format in list text; do
            rlAssertNotGrep 'relevancy' "relevancy-$format.fmf"
            rlAssertGrep 'adjust:' "relevancy-$format.fmf"
            rlAssertGrep 'when: distro == rhel' "relevancy-$format.fmf"
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
