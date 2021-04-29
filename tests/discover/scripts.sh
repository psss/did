#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'set -o pipefail'
        rlRun 'pushd data'
    rlPhaseEnd

    plan='plan --name /smoke'

    rlPhaseStartTest 'Discover only'
        rlRun "tmt run -r discover finish $plan | tee output"
        rlAssertGrep '1 test selected' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Selected steps'
        rlRun "tmt run -r discover provision execute finish $plan | tee output"
        rlAssertGrep '1 test selected' 'output'
        rlAssertGrep 'discover' 'output'
        rlAssertGrep 'provision' 'output'
        rlAssertGrep 'execute' 'output'
        rlAssertGrep 'finish' 'output'
        rlAssertNotGrep 'prepare' 'output'
        rlAssertNotGrep 'report' 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'popd'
        rlRun 'rm -f output' 0 'Removing tmp file'
    rlPhaseEnd
rlJournalEnd
