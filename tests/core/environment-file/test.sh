#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    good="plan --name /plan/good"

    rlPhaseStartTest "Check environment-file option reads properly"
        rlRun -s "tmt run -rvvvddd $good"
        rlAssertGrep "total: 1 test passed" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Check if --environment overwrites --environment-file"
        rlRun "tmt run --environment STR=bad_str -rvvvddd $good 2>&1 \
            | tee output" 1
        rlAssertGrep "AssertionError: assert 'bad_str' == 'O'" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Check if cli environment-file overwrites fmf"
        rlRun "tmt run --environment-file env-via-cli -rvvvddd $good 2>&1 \
            | tee output" 1
        rlAssertGrep "AssertionError: assert '2' == '1'" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Bad dotenv format"
        rlRun "tmt run -rvvvddd plan -n bad 2>&1 | tee output" 2
        rlAssertGrep "Failed to extract variables.*data/bad" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Empty environment file"
        rlRun "tmt run -rvvddd discover finish plan -n empty 2>&1 | tee output"
        rlAssertGrep "warn: Empty environment file" "output"
    rlPhaseEnd

    rlPhaseStartTest "Escape from the tree"
        rlRun "tmt run -rvvvddd plan -n escape 2>&1 | tee output" 2
        rlAssertGrep "path '/etc/secret' is outside" 'output'
    rlPhaseEnd

    rlPhaseStartTest "Fetch a remote file"
        # Good
        rlRun "tmt plan show fetch/good | tee output"
        rlAssertGrep "STR: O" 'output'
        rlAssertGrep "INT: 0" 'output'
        # Bad
        rlRun "tmt plan show fetch/bad 2>&1 | tee output" 2
        rlAssertGrep "Failed to fetch the environment file" 'output'
        rlAssertGrep "Not Found" 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm output'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
