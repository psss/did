#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for node in tests plans stories; do
        rlPhaseStartTest "Select $node"
            # Enabled
            rlRun "tmt $node ls --filter enabled:true | tee output"
            rlAssertGrep "/$node/enabled" "output"
            rlAssertNotGrep "/$node/disabled" "output"
            # Disabled
            rlRun "tmt $node ls --filter enabled:false | tee output"
            rlAssertNotGrep "/$node/enabled" "output"
            rlAssertGrep "/$node/disabled" "output"
        rlPhaseEnd
    done

    for node in tests plans stories; do
        rlPhaseStartTest "Show $node"
            # Enabled
            rlRun "tmt $node show --filter enabled:true | tee output"
            rlAssertGrep "/$node/enabled" "output"
            rlAssertNotGrep "/$node/disabled" "output"
            rlAssertGrep "enabled true" "output"
            # Disabled
            rlRun "tmt $node show --filter enabled:false | tee output"
            rlAssertNotGrep "/$node/enabled" "output"
            rlAssertGrep "/$node/disabled" "output"
            rlAssertGrep "enabled false" "output"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm -r output"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
