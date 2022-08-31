#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Combine shell and beakerlib"
        rlRun -s "tmt run -avvvvdddr"
        # The default test framework should be 'shell'
        rlAssertGrep "Execute '/tests/shell/default' as a 'shell' test." $rlRun_LOG
        # Explicit framework in test should always override default
        rlAssertGrep "Execute '/tests/shell/explicit' as a 'shell' test." $rlRun_LOG
        rlAssertGrep "Execute '/tests/beakerlib' as a 'beakerlib' test." $rlRun_LOG
        # Beakerlib dependency should be detected from framework
        rlAssertGrep "dnf install.*beakerlib" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
