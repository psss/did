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
        rlRun "tmt plan create -t mini plan2"
        rlRun "tmt run -a -S report provision -h local | tee run-output"
        rlRun "runid=\$(head -n 1 run-output)" 0 "Get the run ID"
    rlPhaseEnd

    rlPhaseStartTest "No verbosity"
        rlRun "tmt status | tee output"
        rlAssertGrep "done\s+$runid" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Verbose"
        rlRun "tmt status -v | tee output"
        rlAssertGrep "done\s+$runid\s+/plan1" "output" -E
        rlAssertGrep "done\s+$runid\s+/plan2" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Very verbose"
        rlRun "tmt status -vv | tee output"
        rlAssertGrep "(done\s+){4}todo\s+done\s+$runid\s+/plan1" "output" -E
        rlAssertGrep "(done\s+){4}todo\s+done\s+$runid\s+/plan2" "output" -E
    rlPhaseEnd

    rlPhaseStartTest "Specify ID"
        rlRun "tmt status -i $runid | tee output"
        rlAssertGrep "done\s+$runid" "output" -E
        rlRun "wc -l output | tee lines" 0 "Get the number of lines"
        rlLog "There should be the heading and one run"
        rlAssertGrep "2" "lines"

        rlRun "tmt status -i /not/a/valid/runid | tee output" 0 "Invalid ID"
        rlRun "wc -l output | tee lines" 0 "Get the number of lines"
        rlLog "There should only be the heading"
        rlAssertGrep "1" "lines"
    rlPhaseEnd

    rlPhaseStartTest "Different root"
        rlRun "tmprun=\$(mktemp -d)" 0 "Create a temporary directory for runs"
        rlRun "tmt run -a -i $tmprun/run provision -h local"
        rlRun "tmt status --workdir-root $tmprun | tee output"
        rlRun "wc -l output | tee lines" 0 "Get the number of lines"
        rlLog "The status should only show one run and its heading"
        rlAssertGrep "2" "lines"
    rlPhaseEnd

    rlPhaseStartTest "Filters"
        rlRun "tmt status --finished | tee output"
        rlAssertGrep "done\s+$runid" "output" -E
        # Remove the initial run, we do not need it anymore
        rlRun "rm -r $runid"
        rlRun "tmt run -r provision -h local | tee run-output"
        rlRun "runid=\$(head -n 1 run-output)" 0 "Get the run ID"
        rlRun "tmt status --abandoned | tee output"
        rlAssertGrep "done\s+$runid" "output" -E
        rlRun "tmt run -l finish"

        rlRun "tmt run -ar provision -h local prepare -h shell -s false \
            | tee run-output" 2 "Let the prepare step fail"
        rlRun "runid=\$(head -n 1 run-output)" 0 "Get the run ID"
        rlRun "tmt status --active | tee output"
        rlAssertGrep "todo\s+$runid" "output" -E
        rlRun "tmt run -l finish"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "tmt run -i $runid finish" 0 "Get rid of an active provision"
        rlRun "popd"
        rlRun "rm -r $runid" 0 "Remove the initial testing run"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
        rlRun "rm -r $tmprun" 0 "Remove a temporary directory for runs"
    rlPhaseEnd
rlJournalEnd
