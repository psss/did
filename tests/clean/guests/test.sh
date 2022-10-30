#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
        rlRun "tmt plan create -t mini plan1"
        rlRun "tmt run --until provision provision -h container 2>&1 >/dev/null | tee run-output"
        rlRun "runid=\$(head -n 1 run-output)" 0 "Get the run ID"
    rlPhaseEnd

    rlPhaseStartTest "Dry mode"
        rlRun "tmt status -vv | tee output"
        rlAssertGrep "(done\s+){2}(todo\s+){4}$runid\s+/plan1" "output" -E
        rlRun "tmt clean guests --dry -v 2>&1 >/dev/null | tee output"
        rlAssertGrep "Would stop guests in run '$runid'" "output"
        rlRun "tmt status -vv | tee output"
        rlAssertGrep "(done\s+){2}(todo\s+){4}$runid\s+/plan1" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Specify ID"
        rlRun "tmt clean guests --dry -v -l 2>&1 >/dev/null | tee output"
        rlAssertGrep "Would stop guests in run '$runid'" "output"

        rlRun "tmt clean guests --dry -v -i $runid 2>&1 >/dev/null | tee output"
        rlAssertGrep "Would stop guests in run '$runid'" "output"

        rlRun "tmt status -vv | tee output"
        rlAssertGrep "(done\s+){2}(todo\s+){4}$runid\s+/plan1" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Filter by how"
        rlRun "tmt clean guests --dry -v --how container 2>&1 >/dev/null | tee output"
        rlAssertGrep "Would stop guests in run '$runid'" "output"

        rlRun "tmt clean guests --dry -v --how virtual 2>&1 >/dev/null | tee output"
        rlAssertNotGrep "Would stop guests in run '$runid'" "output"

        rlRun "tmt status -vv | tee output"
        rlAssertGrep "(done\s+){2}(todo\s+){4}$runid\s+/plan1" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Stop the guest"
        rlRun "tmt clean guests -v -i $runid 2>&1 >/dev/null | tee output"
        rlAssertGrep "Stopping guests in run '$runid'" "output"
        rlRun "tmt status -vv | tee output"
        rlAssertGrep "(done\s+){2}(todo\s+){3}done\s+$runid\s+/plan1" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Different root"
        rlRun "tmprun=\$(mktemp -d)" 0 "Create a temporary directory for runs"
        rlRun "tmt run -i $tmprun/run1 --until provision provision -h local 2>&1 >/dev/null | tee run-output"
        rlRun "tmt run -i $tmprun/run2 --until provision provision -h local 2>&1 >/dev/null | tee run-output"
        rlRun "tmt clean guests --workdir-root $tmprun"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlAssertGrep "(done\s+){2}(todo\s+){3}done\s+$tmprun/run1" "output" -E
        rlAssertGrep "(done\s+){2}(todo\s+){3}done\s+$tmprun/run2" "output" -E
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $runid" 0 "Remove initial run"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
        rlRun "rm -r $tmprun" 0 "Remove a temporary directory for runs"
    rlPhaseEnd
rlJournalEnd
