#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt run -avr execute report -h polarion --project-id RHELBASEOS --no-upload --file xunit.xml | tee output" 2
        rlAssertGrep "1 test passed, 1 test failed and 1 error" "output"
        rlAssertGrep '<testsuite disabled="0" errors="1" failures="1" name="/plan" skipped="0" tests="3"' "xunit.xml"
        rlAssertGrep '<property name="polarion-project-id" value="RHELBASEOS" />' "xunit.xml"
        rlAssertGrep '<property name="polarion-testcase-id" value="BASEOS-10914" />' "xunit.xml"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm output xunit.xml"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
