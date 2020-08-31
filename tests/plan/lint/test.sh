#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
        rlRun "tmt plan create --template mini plan"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt plan lint"
    rlPhaseEnd

    rlPhaseStartTest
        # remove the last line (execute definition)
        rlRun "tail -n 1 plan.fmf | wc -c | xargs -I {} truncate plan.fmf -s -{}"
        rlRun "tmt plan lint" 1
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
