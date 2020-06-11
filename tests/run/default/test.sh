#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "options='-av provision -h local'"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "No Metadata"
        rlRun "tmt run $options execute -h shell -s 'touch $tmp/no-metadata'"
        rlAssertExists "$tmp/no-metadata"
    rlPhaseEnd

    rlPhaseStartTest "No Plan"
        rlRun "tmt init"
        rlRun "tmt test create -t shell tests/smoke"
        rlRun "echo 'touch $tmp/no-plan' >> tests/smoke/test.sh"
        rlRun "tmt run $options"
        rlAssertExists "$tmp/no-plan"
        rlRun "tmt run --last report -fv" 0 "Try --last report (verify #287)"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
