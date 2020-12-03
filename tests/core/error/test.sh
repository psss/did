#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "plan errors"
        rlRun "tmt plan ls 2>output" 2 "tmt plan ls without metadata"
        rlRun "cat output"
        rlRun "grep \"No metadata found in the '.' directory. Use 'tmt init' to get started.\" output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -rf output $run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
