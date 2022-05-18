#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
        rlRun "tmt plan create -t mini plan"
        rlRun -s "tmt run provision -h local"
        rlRun "runid=\$(head -n 1 $rlRun_LOG)" 0 "Get the run ID"
    rlPhaseEnd

    rlPhaseStartTest "Verbosity and dryness is propagated"
        rlRun -s "tmt clean -v --dry runs"
        rlAssertGrep "Would remove workdir '$runid'" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Guest is cleaned before run"
        rlRun -s "tmt clean --dry guests runs"
        rlRun "sed -e '/guests/,/runs/!d' $rlRun_LOG > out"
        rlAssertGrep "runs" "out"
        rlAssertGrep "guests" "out"

        rlRun -s "tmt clean -v --dry runs guests"
        # If the order is incorrect, this won't include "runs"
        rlRun "sed -e '/guests/,/runs/!d' $rlRun_LOG > out"
        rlAssertGrep "runs" "out"
        rlAssertGrep "guests" "out"

        rlRun "rm out"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $runid" 0 "Remove initial run"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
