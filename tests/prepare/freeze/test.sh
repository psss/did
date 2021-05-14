#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
    rlPhaseEnd
    rlPhaseStartTest
        # Timeout large enough to boot the VM
        rlRun "rlWatchdog \"rlRun 'tmt run -vfi $tmp' 2\" 60"
        # ^ exitcode has to be 2 (prepare failed)
        rlAssertGrep 'status:.*done' "$tmp/plan/provision/step.yaml"
        rlAssertGrep 'status:.*todo' "$tmp/plan/prepare/step.yaml"
        rlAssertGrep 'status:.*todo' "$tmp/plan/execute/step.yaml"
    rlPhaseEnd
    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
