#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "One line fails"
        rlRun -s "tmt run -i $run plan -n default" 1 "Options make multiline fail"
        rlAssertGrep "1 test failed" $rlRun_LOG
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Override default options"
        rlRun -s "tmt run -i $run plan -n override" 0 "Override the options to pass"
        rlAssertGrep "1 test passed" $rlRun_LOG
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Multiline discovered tests"
        rlRun -s "tmt run -i $run plan -n discovered" 1 "Multiline scripts in tests"
        rlAssertGrep "1 test passed and 1 test failed" $rlRun_LOG
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Listed multiple commands"
        rlRun -s "tmt run -i $run plan -n listed" 1 "Listed script, multiple commands"
        rlAssertGrep "1 test failed" $rlRun_LOG
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $run" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
