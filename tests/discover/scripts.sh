#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'set -o pipefail'
    rlPhaseEnd

    plan='plan --name /plans/smoke'

    rlPhaseStartTest 'All steps'
        rlRun "tmt run discover $plan | tee output"
        rlAssertGrep '1 test selected' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Selected steps'
        rlRun "tmt run discover provision execute $plan | tee output"
        rlAssertGrep '1 test selected' 'output'
        rlAssertGrep 'discover' 'output'
        rlAssertGrep 'provision' 'output'
        rlAssertGrep 'execute' 'output'
        rlAssertNotGrep 'prepare' 'output'
        rlAssertNotGrep 'report' 'output'
        rlAssertNotGrep 'finish' 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
    rlPhaseEnd
rlJournalEnd
