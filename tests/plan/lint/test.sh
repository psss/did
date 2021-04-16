#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Good"
        rlRun -s "tmt plan lint good"
        rlAssertGrep "/good" $rlRun_LOG
        rlAssertNotGrep 'warn summary ' $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt plan lint valid_fmf"
        rlAssertGrep "pass fmf remote id in 'default' is valid" $rlRun_LOG
        rlAssertNotGrep 'warn summary ' $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt plan lint multi_execute"
        rlAssertGrep "/multi_execute" $rlRun_LOG
        rlAssertNotGrep 'fail' $rlRun_LOG
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartTest "Bad"
        rlRun -s "tmt plan lint bad" 1
        rlAssertGrep 'fail execute step must be defined' $rlRun_LOG
        rlAssertGrep 'warn summary is very useful' $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt plan lint invalid_how" 1
        rlAssertGrep "fail unknown discover method 'somehow'" $rlRun_LOG
        rlAssertGrep "fail unsupported execute method 'somehow'" $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt plan lint invalid_url" 1
        rlAssertGrep "fail repo 'http://invalid-url' cannot be cloned" \
            $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt plan lint invalid_ref" 1
        rlAssertGrep "fail git ref 'invalid-ref-123456' is invalid" $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt plan lint invalid_path" 1
        rlAssertGrep "fail path '/invalid-path-123456' is invalid" $rlRun_LOG
        rlRun "rm $rlRun_LOG"

        rlRun -s "tmt plan lint multi_discover" 1
        rlAssertGrep "pass fmf remote id in 'a' is valid" $rlRun_LOG
        rlAssertGrep "fail repo 'http://invalid-url' cannot be cloned" \
            $rlRun_LOG
        rlRun "rm $rlRun_LOG"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
