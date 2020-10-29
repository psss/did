#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Require an available package"
        rlRun "tmt run plan --name available | tee output"
        rlAssertGrep '1 preparation applied' output
    rlPhaseEnd

    rlPhaseStartTest "Require a missing package"
        rlRun "tmt run plan --name missing | tee output" 2
        rlAssertGrep 'Unable to find a match: forest' output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -f output"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
