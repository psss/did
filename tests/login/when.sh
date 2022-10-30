#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "tmt='tmt run -ar provision -h local execute -h tmt -s '"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init -t mini"
    rlPhaseEnd

    rlPhaseStartTest "Skipped"
        rlRun "$tmt true login -w fail -c true 2>&1 >/dev/null | tee output"
        rlAssertGrep "Skipping interactive" "output"
        rlAssertNotGrep "Starting interactive" "output"
    rlPhaseEnd

    rlPhaseStartTest "Enabled"
        rlRun "$tmt false login -w fail -c true 2>&1 >/dev/null | tee output" 1
        rlAssertNotGrep "Skipping interactive" "output"
        rlAssertGrep "Starting interactive" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
