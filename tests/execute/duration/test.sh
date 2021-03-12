#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
    rlPhaseEnd

    for method in tmt detach; do
        rlPhaseStartTest "Test $method"
            rlRun "tmt run -vfi $tmp -a execute -h $method test --name good" 0
            rlRun "tmt run -vfi $tmp -a execute -h $method test --name long" 2
            rlRun -s "tmt run --last report -fvvv" 2
            rlAssertGrep "Maximum test time '3s' exceeded." $rlRun_LOG
            rlAssertGrep "Adjust the test 'duration' attribute" $rlRun_LOG
            rlAssertGrep "spec/tests.html#duration" $rlRun_LOG
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
