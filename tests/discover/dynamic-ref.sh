#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
    rlPhaseEnd

    plan_noctx='plan -n dynamic-ref/no-context'
    plan_ctx='plan -n dynamic-ref/with-context'
    steps='discover finish'

    rlPhaseStartTest 'Check dynamic ref without "branch" context'
        rlRun -s "tmt run -r $plan_noctx $steps" 0,2
        rlAssertGrep 'ref: main' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest 'Check dynamic ref with "branch=fedora"'
        rlRun -s "tmt -c branch=fedora run -r $plan_noctx $steps" 0,2
        rlAssertGrep 'ref: fedora' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest 'Check dynamic ref with "branch=fedora" defined in a test plan'
        rlRun -s "tmt run -r $plan_ctx $steps" 0,2
        rlAssertGrep 'ref: fedora' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest 'Check dynamic ref with context override through --context"'
        rlRun -s "tmt -c branch=rhel run -r $plan_ctx $steps" 0,2
        rlAssertGrep 'ref: rhel' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
