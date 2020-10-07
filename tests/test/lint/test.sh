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

    rlPhaseStartTest "Good"
        rlRun "tmt test lint"
    rlPhaseEnd

    rlPhaseStartTest "Bad"
        # Remove the test script path
        rlRun "sed -i 's/test:.*/test:/' test/main.fmf"
        rlRun "tmt test lint | tee output" 1
        rlAssertGrep 'fail test script must be defined' output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
