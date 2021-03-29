#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest "Dry"
        for option in '-n' '--dry'; do
            rlRun -s "tmt init -t base $option"
            rlAssertGrep "Directory .* would be created." "${rlRun_LOG}"
            rlAssertNotExists "plans/example.fmf"
            rlAssertNotExists "tests/example/main.fmf"
            rlAssertNotExists "tests/example/test.sh"
        done
    rlPhaseEnd

    rlPhaseStartTest "Create"
        rlRun -s "tmt init -t base"
        rlAssertGrep "Tree .* initialized." "${rlRun_LOG}"
        rlAssertGrep "Applying template 'base'." "${rlRun_LOG}"
        rlAssertGrep "Directory .* created." "${rlRun_LOG}"
        rlAssertExists "plans/example.fmf"
        rlAssertExists "tests/example/main.fmf"
        rlAssertExists "tests/example/test.sh"
    rlPhaseEnd

    rlPhaseStartTest "Execute"
        rlRun -s "tmt run -ar provision -h local"
        rlAssertGrep "total: 1 test passed" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
