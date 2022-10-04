#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "workdir=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'pushd data'
    rlPhaseEnd

    plan='plan --name /tests'

    rlPhaseStartTest
        rlRun -s "tmt run --id $workdir -vvv  $plan"
        rlAssertGrep "package: 1 package requested" "$rlRun_LOG" -F
        rlAssertGrep "test: Concise summary" "$rlRun_LOG" -F
        rlAssertGrep '00:00:00 pass /first (original result: fail) [1/2]' "$rlRun_LOG" -F
        rlAssertGrep '00:00:00 pass /second [2/2]' "$rlRun_LOG" -F
    rlPhaseEnd

    # Attribute 'adjust' is not applied
    # Attributes 'tier', 'link', 'tag', 'component' are not usable for filtering
    # 'require' and 'recommend' doesn't accept fmf-id dictionary

    rlPhaseStartCleanup
        rlRun 'popd'
        rlRun "rm -rf $workdir" 0 'Remove tmp directory'
    rlPhaseEnd
rlJournalEnd
