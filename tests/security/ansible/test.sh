#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create a run directory"
        rlRun "secret=\$(mktemp /tmp/secret.XXX)" 0 "Create a secret file"
        rlRun "echo revealed > $secret" 0 "Add a secret content"
        rlRun "pushd data"
    rlPhaseEnd

    for method in ${METHODS:-container}; do
        rlPhaseStartTest "Test ($method)"
            rlRun -s "tmt run --id $run -avvvddd provision -h $method" 1-3
            rlAssertNotGrep "revealed" $rlRun_LOG
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run $secret" 0 "Remove run and secret"
    rlPhaseEnd
rlJournalEnd
