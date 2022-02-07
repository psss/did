#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "set -o pipefail"
        rlRun "pushd multi-part-data"
    rlPhaseEnd

    rlPhaseStartTest "Simple reboot test"
        rlRun -s "tmt run -a execute -vvv"
        rlRun "grep Rebooted $rlRun_LOG | wc -l > reboots"
        rlAssertGrep "2" "reboots"
        rlRun "rm reboots"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf output $run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
