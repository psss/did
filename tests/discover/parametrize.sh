#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    plan='plan -n parametrize/noenvironment'
    plan_env='plan -n parametrize/environment'
    steps='discover finish'
    rlPhaseStartTest 'From environment attribute'
        rlRun "tmt run -r $plan_env $steps | tee output"
        rlAssertGrep 'url: https://github.com/teemtee/tmt' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'From command line'
        rlRun "tmt run -r -e REPO=tmt $plan $steps | tee output"
        rlAssertGrep 'url: https://github.com/teemtee/tmt' 'output'
        # Precedence of option over environment attribute
        rlRun "tmt run -r -e REPO=fmf $plan_env $steps | tee output"
        rlAssertGrep 'url: https://github.com/teemtee/fmf' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Process environment should be ignored'
        rlRun "REPO=fmf tmt run -r $plan_env $steps | tee output"
        rlAssertGrep 'url: https://github.com/teemtee/tmt' 'output'
        # No substitution should happen
        rlRun "REPO=tmt tmt run -r $plan $steps | tee output" 2
        rlAssertGrep 'url: https://github.com/teemtee/${REPO}' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Undefined variable'
        rlRun "tmt run -r $plan $steps | tee output" 2
        rlAssertGrep 'url: https://github.com/teemtee/${REPO}' 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
