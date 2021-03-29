#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt init -t full -n"
        rlAssertGrep "Directory .* would be created." "${rlRun_LOG}"
        rlAssertNotExists "stories/example.fmf"
        rlAssertNotExists "plans/example.fmf"
        rlAssertNotExists "tests/example/main.fmf"
        rlAssertNotExists "tests/example/test.sh"
        rlRun -s "tmt init -t full"
        rlAssertGrep "Tree .* initialized." "${rlRun_LOG}"
        rlAssertGrep "Applying template 'full'." "${rlRun_LOG}"
        rlAssertGrep "Directory .* created." "${rlRun_LOG}"
        rlAssertExists "stories/example.fmf"
        rlAssertExists "plans/example.fmf"
        rlAssertExists "tests/example/main.fmf"
        rlAssertExists "tests/example/test.sh"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
