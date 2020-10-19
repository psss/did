#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "tmt='tmt run -a provision -h local'"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init -t mini"
    rlPhaseEnd

    rlPhaseStartTest "No login"
        rlRun "$tmt | tee output"
        rlAssertNotGrep "interactive" "output"
    rlPhaseEnd

    rlPhaseStartTest "Last step"
        rlRun "$tmt login -c true | tee output"
        rlAssertGrep "interactive" "output"
        rlRun "grep '^    finish$' -A4 output | grep -i interactive"
    rlPhaseEnd

    rlPhaseStartTest "Selected step"
        rlRun "$tmt login -c true -s discover | tee output"
        rlAssertGrep "interactive" "output"
        rlRun "grep '^    discover$' -A4 output | grep -i interactive"
    rlPhaseEnd

    rlPhaseStartTest "Failed command"
        rlRun "$tmt login -c false | tee output"
        rlAssertGrep "interactive" "output"
    rlPhaseEnd

    rlPhaseStartTest "Last run"
        rlRun "$tmt"
        rlRun "tmt run -l login -c true | tee output"
        rlAssertGrep "interactive" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
