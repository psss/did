#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "set -o pipefail"
        rlRun "pushd shorten-timeout-data"
    rlPhaseEnd

    rlPhaseStartTest "Reboot with a very short reconnect timeout"
        rlRun -s "tmt run -a execute -vvv" 2
        rlAssertGrep "summary: 1 error" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf output $run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
