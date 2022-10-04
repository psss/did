#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Custom Script"
        rlRun "tmt run -rv plan -n custom" 0 "Prepare using a custom script"
    rlPhaseEnd

    rlPhaseStartTest "Commandline Script"
        rlRun "tmt run -arv plan -n custom \
            prepare -h shell -s './prepare.sh'" 0 "Prepare using a custom script from cmdline"
    rlPhaseEnd

    rlPhaseStartTest "Multiple Commandline Scripts"
        rlRun "tmt run -arv plans -n multiple \
            prepare -h shell -s 'touch /tmp/first' -s 'touch /tmp/second'"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
