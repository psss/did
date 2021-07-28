#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest "Check environment-file option reads properly"
        rlRun "tmt run -vvvddd | tee output"
        rlAssertGrep "total: 1 test passed" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Check if --environment overwrites --environment-file"
        rlRun "tmt run --environment STR=bad_str -vvvddd 2>&1 | tee output" 1
        rlAssertGrep "AssertionError: assert 'bad_str' == 'O'" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Check if cli environment-file overwrites fmf"
        rlRun "tmt run --environment-file env-via-cli -vvvddd 2>&1 | tee output" 1
        rlAssertGrep "AssertionError: assert '2' == '1'" 'output'
    rlPhaseEnd
rlJournalEnd
