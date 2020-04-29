#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data/parent/child'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest 'Import metadata'
        rlRun 'tmt test import --no-nitrate'
        rlAssertGrep 'summary: Simple smoke test' 'main.fmf'
    rlPhaseEnd

    rlPhaseStartTest 'Check duplicates'
        rlAssertNotGrep 'component:' 'main.fmf'
        rlAssertNotGrep 'test:' 'main.fmf'
        rlAssertNotGrep 'duration:' 'main.fmf'
    rlPhaseEnd

    rlPhaseStartTest 'Verify inheritance'
        rlRun 'tmt test show | tee output'
        rlAssertGrep 'component tmt' 'output'
        rlAssertGrep 'test ./runtest.sh' 'output'
        rlAssertGrep 'duration 5m' 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm output main.fmf'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
