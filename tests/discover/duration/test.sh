#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Check default and defined durations"
        rlRun "tmt run --id $tmp discover"

        # Check default durations
        path=$tmp/plan/default
        rlAssertGrep 'duration: 5m' $path/fmf/discover/tests.yaml
        rlAssertGrep 'duration: 1h' $path/discover/discover/tests.yaml
        rlAssertGrep 'duration: 1h' $path/execute/discover/tests.yaml

        # Check defined durations
        path=$tmp/plan/defined
        rlAssertGrep 'duration: 3h' $path/fmf/discover/tests.yaml
        rlAssertGrep 'duration: 4h' $path/execute/discover/tests.yaml
        rlAssertGrep 'duration: 5h' $path/discover/discover/tests.yaml
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
