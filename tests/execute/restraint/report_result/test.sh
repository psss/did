#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "set -o pipefail"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest 'Verify mocked Restraint rstrnt-report-result file generated correctly and read by tmt.'
        rlRun "tmt run -vvvddd --remove | tee $output" 1 "Execute smoke tests."
        rlAssertGrep "Rstrnt-report-result output file detected." $output
        rlAssertGrep "pass /smoke/good" $output
        rlAssertGrep "pass /smoke/bad" $output
        rlAssertGrep "info /smoke/skip" $output
        rlAssertGrep "warn /smoke/warn" $output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
        rlRun "rm $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
