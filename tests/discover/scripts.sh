#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
    rlPhaseEnd

    plan='plan --name /smoke'

    rlPhaseStartTest 'Discover only'
        rlRun -s "tmt run --id XXX --scratch --remove $plan"
        rlAssertGrep '1 test selected' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest 'Selected steps'
        rlRun -s "tmt run -r discover provision execute finish $plan"
        rlAssertGrep '1 test selected' $rlRun_LOG
        rlAssertGrep 'discover' $rlRun_LOG
        rlAssertGrep 'provision' $rlRun_LOG
        rlAssertGrep 'execute' $rlRun_LOG
        rlAssertGrep 'finish' $rlRun_LOG
        rlAssertNotGrep 'prepare' $rlRun_LOG
        rlAssertNotGrep 'report' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
