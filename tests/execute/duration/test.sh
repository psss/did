#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
    rlPhaseEnd

    for execute_method in tmt; do
        for provision_method in ${PROVISION_METHODS:-local container}; do
            rlPhaseStartTest "Test provision $provision_method, execute $execute_method, short tests"
                rlRun -s "tmt run --scratch -vfi $tmp -a provision -h $provision_method execute -h $execute_method test --name short" 0

                rlRun "grep 'duration \"5\" exceeded' $tmp/log.txt" 1
            rlPhaseEnd

            rlPhaseStartTest "Test provision $provision_method, execute $execute_method, long tests"
                rlRun -s "tmt run --scratch -vfi $tmp -a provision -h $provision_method execute -h $execute_method test --name long 2>&1" 2
                rlAssertNotGrep "00:02:.. errr /test/long/beakerlib (timeout)" $rlRun_LOG
                rlAssertNotGrep "00:02:.. errr /test/long/shell (timeout)" $rlRun_LOG

                rlRun -s "tmt run --last report -fvvvv 2>&1" 2
                rlAssertGrep "Maximum test time '5s' exceeded." $rlRun_LOG
                rlAssertGrep "Adjust the test 'duration' attribute" $rlRun_LOG
                rlAssertGrep "spec/tests.html#duration" $rlRun_LOG

                rlRun -s "grep -A4 'duration \"5\" exceeded' $tmp/log.txt"

                rlRun "egrep ' [[:digit:]]{1,2}\.[[:digit:]]+ sent SIGKILL signal' $rlRun_LOG"
                rlRun "egrep ' [[:digit:]]{1,2}\.[[:digit:]]+ kill confirmed' $rlRun_LOG"
                rlRun "egrep ' [[:digit:]]{1,2}\.[[:digit:]]+ waiting for stream readers' $rlRun_LOG"
                rlRun "egrep ' [[:digit:]]{1,2}\.[[:digit:]]+ stdout reader done' $rlRun_LOG"
            rlPhaseEnd
        done
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
