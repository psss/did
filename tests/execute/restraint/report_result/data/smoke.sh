#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "set -o pipefail"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest 'Verify mocked Restraint rstrnt-report-result file generated correctly.'
        rlRun "tmt run provision -h container -ddd"
        rlRun "rm -f $TMT_TEST_DATA/reportResult" 0 "Report file successfully removed pre test."
        rlRun "rstrnt-report-result --server http://test-example.com report SKIP" 0 "Generating Restraint report of skipped test."
        rlRun "ls $TMT_TEST_DATA/reportResult" 0 "Result report successfully generated."
        rlRun "cat $TMT_TEST_DATA/reportResult | tee output"
        rlAssertGrep 'TESTRESULT=SKIP' 'output'
        rlRun "rstrnt-report-result --server http://test-example.com --port 55 --disable-plugin avc --message 'Example output message.' -o /tmp/example_output.txt report PASS 66" 0 "Generating Restraint report of passed test."
        rlRun "cat $TMT_TEST_DATA/reportResult | tee output"
        rlAssertGrep 'SERVER=http://test-example.com' 'output'
        rlAssertGrep 'PORT=55' 'output'
        rlAssertGrep 'MESSAGE=Example output message.' 'output'
        rlAssertGrep 'OUTPUTFILE=/tmp/example_output.txt' 'output'
        rlAssertGrep 'DISABLEPLUGIN=avc' 'output'
        rlAssertGrep 'TESTNAME=report' 'output'
        rlAssertGrep 'TESTRESULT=PASS' 'output'
        rlAssertGrep 'METRIC=66' 'output'
        rlRun "rstrnt-report-result --server http://test-example.com report WARN" 0 "Generating Restraint report of warned test."
        rlRun "cat $TMT_TEST_DATA/reportResult | tee output"
        rlAssertGrep 'TESTRESULT=WARN' 'output'
        rlRun "rstrnt-report-result --server http://test-example.com report FAIL" 0 "Generating Restraint report of failed test."
        rlRun "cat $TMT_TEST_DATA/reportResult | tee output"
        rlAssertGrep 'TESTRESULT=FAIL' 'output'
        rlRun "rm -f $TMT_TEST_DATA/reportResult" 0 "Report file successfully removed post test."
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
