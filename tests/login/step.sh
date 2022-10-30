#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "tmt='tmt run -ar provision -h local'"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init -t mini"
    rlPhaseEnd

    rlPhaseStartTest "No login"
        rlRun "$tmt 2>&1 >/dev/null | tee output"
        rlAssertNotGrep "interactive" "output"
    rlPhaseEnd

    rlPhaseStartTest "Last step"
        rlRun "$tmt login -c true 2>&1 >/dev/null | tee output"
        rlAssertGrep "interactive" "output"
        rlRun "grep '^    finish$' -A4 output | grep -i interactive"
    rlPhaseEnd

    for step in discover provision prepare execute report finish; do
        rlPhaseStartTest "Selected step ($step)"
            rlRun "$tmt login -c true -s $step 2>&1 >/dev/null | tee output"
            rlAssertGrep "interactive" "output"
            rlRun "grep '^    $step$' -A4 output | grep -i interactive"
        rlPhaseEnd
    done

    rlPhaseStartTest "Failed command"
        rlRun "$tmt login -c false 2>&1 >/dev/null | tee output"
        rlAssertGrep "interactive" "output"
    rlPhaseEnd

    rlPhaseStartTest "Last run"
        rlRun "tmt run -a provision -h local"
        rlRun "tmt run -rl login -c true 2>&1 >/dev/null | tee output"
        rlAssertGrep "interactive" "output"
    rlPhaseEnd

    rlPhaseStartTest "Last run failed"
        rlRun "tmt run provision -h local prepare --how shell --script false" 2
        rlRun "tmt run -rl login -c true 2>&1 >/dev/null | tee output" 2
        rlAssertGrep "interactive" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
