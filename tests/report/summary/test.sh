#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Check summary"
        rlRun "tmt run -r 2>&1 >/dev/null | tee output" 2 "Run tests in concise mode"
        rlAssertGrep "3 tests passed, 2 tests failed and 1 error" "output"
    rlPhaseEnd

    rlPhaseStartTest "Check details"
        rlRun "tmt run -v 2>&1 >/dev/null | tee output" 2 "Run tests in verbose mode"
        rlAssertGrep "fail /test/bad/one" "output"
        rlAssertGrep "fail /test/bad/two" "output"
        rlAssertGrep "pass /test/good/one" "output"
        rlAssertGrep "pass /test/good/three" "output"
        rlAssertGrep "pass /test/good/two" "output"
        rlAssertGrep "errr /test/weird/one" "output"
    rlPhaseEnd

    rlPhaseStartTest "Check the last run"
        rlRun "tmt run -l 2>&1 >/dev/null | tee output" 2 "Last run in concise mode "
        rlAssertGrep "3 tests passed, 2 tests failed and 1 error" "output"
        rlRun "tmt run -lvr 2>&1 >/dev/null | tee output" 2 "Last run in verbose mode "
        rlAssertGrep "3 tests passed, 2 tests failed and 1 error" "output"
        rlAssertGrep "fail /test/bad/one" "output"
        rlAssertGrep "pass /test/good/one" "output"
        rlAssertGrep "errr /test/weird/one" "output"
    rlPhaseEnd


    rlPhaseStartCleanup
        rlRun "rm output" 0 "Removing tmp directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
