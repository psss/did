#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
        rlRun "tmt plan create --template mini good"
        rlRun "echo 'execute:' > bad.fmf"
    rlPhaseEnd

    rlPhaseStartTest "Good"
        rlRun "tmt plan lint good"
    rlPhaseEnd

    rlPhaseStartTest "Bad"
        rlRun "tmt plan lint bad | tee output" 1
        rlAssertGrep 'fail execute step must be defined' output
        rlAssertGrep 'warn summary is very useful' output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
