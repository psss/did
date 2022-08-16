#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

METHODS=${METHODS:-virtual.testcloud}

SRC_PLAN="$(pwd)/data/plan.fmf"

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
    rlPhaseEnd

    rlPhaseStartTest "All options used in plan"
        rlRun "cp $SRC_PLAN ."
        if ! rlRun "tmt run -i $run --scratch"; then
            rlRun "cat $run/log.txt" 0 "Dump log.txt"
        fi
    rlPhaseEnd

    rlPhaseStartTest "All options used in plan from cmdline"
        rlRun "cp $SRC_PLAN ."
        if ! rlRun "tmt run -i $run --scratch --all \
        provision -h virtual.testcloud --image fedora --disk 10 --memory 2048 --connection system"; then
            rlRun "cat $run/log.txt" 0 "Dump log.txt"
        fi
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
