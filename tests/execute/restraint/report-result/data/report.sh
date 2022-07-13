#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

RESULT_FILE="$TMT_TEST_DATA/restraint-result"

rlJournalStart
    rlPhaseStartSetup
        rlRun "rm -f $RESULT_FILE" 0 "Report file successfully removed pre test."
    rlPhaseEnd

    rlPhaseStartTest 'Verify mocked Restraint rstrnt-report-result file generated correctly.'
        rlRun "rstrnt-report-result --server http://test-example.com report SKIP" 0 "Generating Restraint report of skipped test."
        rlRun "ls $RESULT_FILE" 0 "Result report successfully generated."
        rlRun -s "cat $RESULT_FILE"
        rlAssertGrep 'TESTRESULT=SKIP' $rlRun_LOG
        rlRun "rstrnt-report-result --server http://test-example.com --port 55 --disable-plugin avc --message 'Example output message.' -o /tmp/example_output.txt report PASS 66" 0 "Generating Restraint report of passed test."
        rlRun -s "cat $RESULT_FILE"
        rlAssertGrep 'SERVER=http://test-example.com' $rlRun_LOG
        rlAssertGrep 'PORT=55' $rlRun_LOG
        rlAssertGrep 'MESSAGE=Example output message.' $rlRun_LOG
        rlAssertGrep 'OUTPUTFILE=/tmp/example_output.txt' $rlRun_LOG
        rlAssertGrep 'DISABLEPLUGIN=avc' $rlRun_LOG
        rlAssertGrep 'TESTNAME=report' $rlRun_LOG
        rlAssertGrep 'TESTRESULT=PASS' $rlRun_LOG
        rlAssertGrep 'METRIC=66' $rlRun_LOG
        rlRun "rstrnt-report-result --server http://test-example.com report WARN" 0 "Generating Restraint report of warned test."
        rlRun -s "cat $RESULT_FILE"
        rlAssertGrep 'TESTRESULT=WARN' $rlRun_LOG
        rlRun "rstrnt-report-result --server http://test-example.com report FAIL" 0 "Generating Restraint report of failed test."
        rlRun -s "cat $RESULT_FILE"
        rlAssertGrep 'TESTRESULT=FAIL' $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -f $TMT_TEST_DATA/reportResult" 0 "Report file successfully removed post test."
    rlPhaseEnd
rlJournalEnd
