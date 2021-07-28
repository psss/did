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
        rlAssertGrep 'url: https://github.com/psss/tmt' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'From command line'
        rlRun "tmt run -r -e REPO=tmt $plan $steps | tee output"
        rlAssertGrep 'url: https://github.com/psss/tmt' 'output'
        # Precedence of option over environment attribute
        rlRun "tmt run -r -e REPO=fmf $plan_env $steps | tee output"
        rlAssertGrep 'url: https://github.com/psss/fmf' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'From existing environment'
        rlRun "REPO=tmt tmt run -r $plan $steps | tee output"
        rlAssertGrep 'url: https://github.com/psss/tmt' 'output'
        # Precedence of existing environment over environment attribute
        rlRun "REPO=fmf tmt run -r $plan_env $steps | tee output"
        rlAssertGrep 'url: https://github.com/psss/fmf' 'output'
        # Precedence of existing environment over option
        rlRun "REPO=fmf tmt run -r -e REPO=tmt $plan_env $steps | tee output"
        rlAssertGrep 'url: https://github.com/psss/fmf' 'output'
        rlRun "REPO=fmf tmt run -r -e REPO=tmt $plan $steps | tee output"
        rlAssertGrep 'url: https://github.com/psss/fmf' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Undefined variable'
        rlRun "tmt run -r $plan $steps | tee output" 2
        rlAssertGrep 'url: https://github.com/psss/${REPO}' 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
