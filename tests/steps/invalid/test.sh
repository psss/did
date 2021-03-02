
#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "cp data/plan $tmp/plan.fmf"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt run 2>&1 | tee output" 2 "Expect the run to fail"
        rlAssertGrep "Unsupported provision method" "output"
        rlRun "tmt run discover 2>&1 | tee output" 0 "Invalid step not enabled, do not fail"
        rlAssertGrep "warn: Unsupported provision method" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
