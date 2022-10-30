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
        rlRun "tmprun=\$(mktemp -d)" 0 "Create a temporary directory for runs"

        rlRun "run1=$tmprun/1"
        rlRun "tmt run -i $run1 discover"

        rlRun "run2=$tmprun/2"
        rlRun "tmt run -i $run2 discover"
    rlPhaseEnd

    rlPhaseStartTest "Dry mode"
        rlRun "tmt clean runs --dry -v --workdir-root $tmprun 2>&1 >/dev/null | tee output"
        rlAssertGrep "Would remove workdir '$run1'" "output"
        rlAssertGrep "Would remove workdir '$run2'" "output"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlAssertGrep "(done\s+){1}(todo\s+){5}$run1\s+/plan1" "output" -E
        rlAssertGrep "(done\s+){1}(todo\s+){5}$run2\s+/plan1" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Specify ID"
        rlRun "tmt clean runs -v -i $run1 2>&1 >/dev/null | tee output"
        rlAssertGrep "Removing workdir '$run1'" "output"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlAssertNotGrep "(done\s+){1}(todo\s+){5}$run1\s+/plan1" "output" -E
        rlAssertGrep "(done\s+){1}(todo\s+){5}$run2\s+/plan1" "output" -E

        rlRun "tmt clean runs -v -l 2>&1 >/dev/null | tee output"
        rlAssertGrep "Removing workdir '$run2'" "output"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlAssertNotGrep "(done\s+){1}(todo\s+){5}$run2\s+/plan1" "output" -E

        rlRun "wc -l output | tee lines" 0 "Get the number of lines"
        rlLog "The status should only contain the heading"
        rlAssertGrep "1" "lines"
    rlPhaseEnd

    rlPhaseStartTest "Keep N"
        for i in $(seq 1 10); do
            rlRun "tmt run -i $tmprun/$i discover"
        done
        rlRun "tmt clean runs -v --keep 10 --workdir-root $tmprun"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlLog "The runs should remain intact"
        for i in $(seq 1 10); do
            rlAssertGrep "$tmprun/$i\s+/plan1" "output" -E
        done

        rlRun "tmt clean runs -v --keep 2 --workdir-root $tmprun"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlAssertGrep "$tmprun/9" "output"
        rlAssertGrep "$tmprun/10" "output"

        for i in $(seq 1 8); do
            rlAssertNotGrep "$tmprun/$i\s+/plan1" "output" -E
        done

        rlRun "tmt clean runs -v --keep 1 --workdir-root $tmprun"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlAssertNotGrep "$tmprun/9" "output"
        rlAssertGrep "$tmprun/10" "output"

        rlRun "tmt clean runs -v --keep 0 --workdir-root $tmprun"
        rlRun "tmt status --workdir-root $tmprun -vv | tee output"
        rlAssertNotGrep "$tmprun/10" "output"
    rlPhaseEnd

    rlPhaseStartTest "Remove everything"
        for i in $(seq 1 10); do
            rlRun "tmt run -i $tmprun/$i discover"
        done
        rlRun "tmt clean runs -v --workdir-root $tmprun"
        rlRun "tmt status -vv --workdir-root $tmprun | tee output"
        rlRun "wc -l output | tee lines" 0 "Get the number of lines"
        rlLog "The status should only contain the heading"
        rlAssertGrep "1" "lines"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
        rlRun "rm -r $tmprun" 0 "Remove a temporary directory for runs"
    rlPhaseEnd
rlJournalEnd
