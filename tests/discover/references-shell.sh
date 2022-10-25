#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory for failed run"
        rlRun 'pushd data'
    rlPhaseEnd

    plan=shell/url/static
    rlPhaseStartTest $plan
        rlRun -s 'tmt run --id $tmp/run discover -v plan --name $plan'
        discovered_workdir="$tmp/run/plans/$plan/discover/default-0/tests"
        rlAssertExists "$discovered_workdir/tmt.spec"
        # .git is intentionally removed
        rlAssertNotExists "$discovered_workdir/.git"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
