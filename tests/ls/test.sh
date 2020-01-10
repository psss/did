#!/bin/bash

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

examples="/usr/share/doc/tmt/examples/systemd"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm "tmt"
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "cp example-test.txt $TmpDir/test.fmf"
        rlRun "cp example-plan.txt $TmpDir/plan.fmf"
        rlRun "cp example-story.txt $TmpDir/story.fmf"
        rlRun "pushd $TmpDir"
        rlRun "tmt init"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Test listing available tests"
        rlRun "tmt test ls | tee output"
        rlAssertGrep "/test/basic/smoke" "output"
        rlAssertNotGrep "/plan/smoke" "output"
    rlPhaseEnd

    rlPhaseStartTest "Test listing available plans"
        rlRun "tmt plan ls | tee output"
        rlAssertGrep "/plan/smoke" "output"
        rlAssertNotGrep "/test/basic/smoke" "output"
    rlPhaseEnd

    rlPhaseStartTest "Test listing available stories"
        rlRun "tmt story ls | tee output"
        rlAssertGrep "/stories/cli/story/ls" "output"
        rlAssertNotGrep "/test/basic/smoke" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
