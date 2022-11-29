#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "set -o pipefail"
        rlRun "pushd data"
        rlRun "git init"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt --root tests run --keep -i $run" 0
        rlAssertNotExists "$run/plan/discover/default-0/tests/foo"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt --root tests run --keep --scratch -ai $run discover -h fmf --sync-repo" 0
        rlAssertExists "$run/plan/discover/default-0/tests/foo"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -r $run .git" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
