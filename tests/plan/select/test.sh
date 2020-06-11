#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init -t mini"
    rlPhaseEnd

    rlPhaseStartTest "tmt plan ls"
        rlRun "tmt plan ls | tee output"
        rlAssertGrep "/plans/example" output
        rlRun "tmt plan ls example | tee output"
        rlAssertGrep "/plans/example" output
        rlRun "tmt plan ls non-existent | tee output"
        rlAssertNotGrep "/plans/example" output
        rlRun '[[ $(wc -l <output) == "0" ]]' 0 "Check no output"
    rlPhaseEnd

    rlPhaseStartTest "tmt run plan --name"
        tmt='tmt run -ar provision -h local'
        rlRun "$tmt plan --name example | tee output"
        rlAssertGrep "/plans/example" output
        rlRun "$tmt plan --name non-existent | tee output" 2
        rlAssertGrep "No plans found." output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
