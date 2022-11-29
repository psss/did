#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "tmp1=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "tmp2=\$(mktemp -d)" 0 "Creating tmp directory"
    rlPhaseEnd

    rlPhaseStartTest "Check pruning"
        rlRun "tmt run -i $tmp1 -a"
        rlAssertNotExists $tmp1/plan/tree
        rlAssertNotExists $tmp1/plan/discover/default-0
        rlAssertNotExists $tmp1/plan/discover/default-1
        rlAssertExists $tmp1/plan/data/out-plan.txt
        rlAssertExists $tmp1/plan/execute/data/default-2/write/test-data/data/out-test.txt
        for step in discover execute finish prepare provision report; do
            rlAssertExists $tmp1/plan/$step/step.yaml
        done
    rlPhaseEnd

    rlPhaseStartTest "Check Keeping"
        rlRun "tmt run --keep -i $tmp2 -a"
        rlAssertExists $tmp2/plan/tree
        rlAssertExists $tmp2/plan/discover/default-0
        rlAssertExists $tmp2/plan/discover/default-1
        rlAssertExists $tmp2/plan/data/out-plan.txt
        rlAssertExists $tmp2/plan/execute/data/default-2/write/test-data/data/out-test.txt
        for step in discover execute finish prepare provision report; do
            rlAssertExists $tmp2/plan/$step/step.yaml
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp1" 0 "Removing tmp directory"
        rlRun "rm -r $tmp2" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
