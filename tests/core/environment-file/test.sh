#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest "Check environment-file option reads properly"
        rlRun "tmt run -rvvvddd | tee output"
        rlAssertGrep "total: 1 test passed" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Check if --environment overwrites --environment-file"
        rlRun "tmt run --environment STR=bad_str -rvvvddd 2>&1 | tee output" 1
        rlAssertGrep "AssertionError: assert 'bad_str' == 'O'" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Check if cli environment-file overwrites fmf"
        rlRun "tmt run --environment-file env-via-cli -rvvvddd 2>&1 | tee output" 1
        rlAssertGrep "AssertionError: assert '2' == '1'" 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm output'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
