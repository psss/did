#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "All good"
        rlRun -s "tmt lint good" 0 "Lint correct metadata"
        rlAssertGrep "tests/good" $rlRun_LOG
        rlAssertGrep "plans/good" $rlRun_LOG
        rlAssertGrep "stories/good" $rlRun_LOG
        rlAssertNotGrep "tests/bad" $rlRun_LOG
        rlAssertNotGrep "plans/bad" $rlRun_LOG
        rlAssertNotGrep "stories/bad" $rlRun_LOG
    rlPhaseEnd

    # Check that exit code is correct if only one level is wrong
    for bad in tests plans stories; do
        rlPhaseStartTest "Only bad $bad"
            rlRun -s "tmt lint '($bad/bad|good)'" 1 "Lint wrong $bad"
        rlPhaseEnd
    done

    rlPhaseStartTest "All bad"
        rlRun -s "tmt lint bad" 1 "Lint wrong metadata"
        rlAssertNotGrep "tests/good" $rlRun_LOG
        rlAssertNotGrep "plans/good" $rlRun_LOG
        rlAssertNotGrep "stories/good" $rlRun_LOG
        rlAssertGrep "tests/bad" $rlRun_LOG
        rlAssertGrep "plans/bad" $rlRun_LOG
        rlAssertGrep "stories/bad" $rlRun_LOG
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

    rlPhaseStartTest "Check --fix for tests"
        rlRun -s "tmt lint --fix fix" 0 "Fix the test"
        rlAssertGrep 'relevancy converted into adjust' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
rlJournalEnd
