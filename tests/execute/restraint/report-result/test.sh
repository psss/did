#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt run -vvv --remove" 1
        rlAssertGrep "pass /report" $rlRun_LOG
        rlAssertGrep "pass /smoke/good" $rlRun_LOG
        rlAssertGrep "fail /smoke/bad" $rlRun_LOG
        rlAssertGrep "info /smoke/skip" $rlRun_LOG
        rlAssertGrep "warn /smoke/warn" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
