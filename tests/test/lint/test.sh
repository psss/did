#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
        rlRun "tmt test create --template beakerlib test"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt test lint"
    rlPhaseEnd

    rlPhaseStartTest
        # remove the test script path
        rlRun "sed -i '$ s/\s.*$//' test/main.fmf"
        rlRun "tmt test lint" 1
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
