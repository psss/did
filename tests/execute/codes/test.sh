#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest
        tmt="tmt run -ar provision -h local"
        rlRun "$tmt execute -h tmt -s true" 0 "Good test"
        rlRun "$tmt execute -h tmt -s false" 1 "Bad test"
        rlRun "$tmt execute -h tmt -s fooo" 2 "Weird test"
        rlRun "$tmt" 3 "No tests"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
