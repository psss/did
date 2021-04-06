#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest "Single Command"
        rlRun "tmt run -r provision -h container login -c 'echo hi' finish"
    rlPhaseEnd

    rlPhaseStartTest "Multiple Commands"
        rlRun "tmt run provision -h container"
        for attempt in one two three; do
            rlRun "tmt run -l login -c 'echo $attempt'"
        done
        rlRun "tmt run -rl finish"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
