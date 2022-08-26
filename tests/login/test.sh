#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Login enabled after tests"
        rlRun -s "tmt run -a plan -n /fmf-tests login -t -c true" 1
        rlAssertEquals "There should 5 occurences of login" $(grep "Starting interactive" $rlRun_LOG | wc -l) "5"
        rlAssertNotGrep "Skipping interactive" $rlRun_LOG
        rlAssertGrep "Starting interactive" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Login enabled after tests and after steps"
        rlRun -s "tmt run -a plan -n /fmf-tests login -t -c true -s discover -s prepare" 1
        rlAssertEquals "There should 6 occurences of login" $(grep "Starting interactive" $rlRun_LOG | wc -l) "6"
        rlAssertNotGrep "Skipping interactive" $rlRun_LOG
        rlAssertGrep "Starting interactive" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Login enabled after failed tests and during report step if fail"
        rlRun -s "tmt run -a plan -n /fmf-tests login -t -c true -s report -w fail" 1
        rlAssertEquals "There should 2 occurences of login" $(grep "Starting interactive" $rlRun_LOG | wc -l) "2"
        rlAssertGrep "Starting interactive" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Verify correct directory after test execution"
      rlRun -s "tmt  run -a plans --name /fmf-tests login -t -c pwd" 1
      rlAssertGrep "/fmf-tests/discover/default-0/tests/tests/test1" $rlRun_LOG
      rlAssertGrep "/fmf-tests/discover/default-0/tests/tests/test2" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
