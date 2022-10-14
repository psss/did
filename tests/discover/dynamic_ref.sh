#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    plan_noctx='plan -n dynamic_ref_noctx'
    plan_ctx='plan -n dynamic_ref_ctx'
    steps='discover finish'

    rlPhaseStartTest 'Check dynamic ref without "branch" context'
        rlRun "tmt run -r $plan_noctx $steps | tee output" 0,2
        rlAssertGrep 'ref: main' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Check dynamic ref with "branch=fedora"'
        rlRun "tmt -c branch=fedora run -r $plan_noctx $steps | tee output" 0,2
        rlAssertGrep 'ref: fedora' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Check dynamic ref with "branch=fedora" defined in a test plan'
        rlRun "tmt run -r $plan_ctx $steps | tee output" 0,2
        rlAssertGrep 'ref: fedora' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Check dynamic ref with context override through --context"'
        rlRun "tmt -c branch=rhel run -r $plan_ctx $steps | tee output" 0,2
        rlAssertGrep 'ref: rhel' 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
