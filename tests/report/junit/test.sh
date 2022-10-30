#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for method in tmt; do
        rlPhaseStartTest "$method"
            rlRun "tmt run -avr execute -h $method report -h junit --file junit.xml 2>&1 >/dev/null | tee output" 2
            rlAssertGrep "2 tests passed, 2 tests failed and 2 errors" "output"
            rlAssertGrep '<testsuite disabled="0" errors="2" failures="2" name="/plan" skipped="0" tests="6"' "junit.xml"
            rlAssertGrep 'fail</failure>' "junit.xml"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm output junit.xml"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
