#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt lint" 1 "Check lint command"
        # linting story
        rlAssertGrep "warn summary should not exceed 50 characters" $rlRun_LOG
        rlAssertGrep "fail unknown attribute 'exampleee' is used" $rlRun_LOG
        # linting test
        rlAssertGrep "pass test script must be defined" $rlRun_LOG
        rlAssertGrep "pass directory path must be absolute" $rlRun_LOG
        rlAssertGrep "pass directory path must exist" $rlRun_LOG
        rlAssertGrep "warn summary is very useful for quick inspection"   \
            $rlRun_LOG
        rlAssertGrep "fail unknown attribute 'summarrry' is used" $rlRun_LOG
        #linting plan
        rlAssertGrep "fail unknown attribute 'discovery' is used" $rlRun_LOG
        rlAssertGrep "fail unknown attribute 'prepareahoj' is used" $rlRun_LOG
    rlPhaseEnd
    rlPhaseStartCleanup
        rlRun "popd"
rlJournalEnd
