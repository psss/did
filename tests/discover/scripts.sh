#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'set -o pipefail'
    rlPhaseEnd

    plan='plan --name smoke'

    rlPhaseStartTest 'All steps'
        rlRun "tmt run $plan | tee output"
        rlAssertGrep '1 test selected' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Selected steps'
        rlRun "tmt run discover execute $plan | tee output"
        rlAssertGrep '1 test selected' 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
    rlPhaseEnd
rlJournalEnd
