#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd $tmp"
        rlRun -s "tmt init -t full -n"
        rlAssertGrep "Directory .* would be created." "${rlRun_LOG}"
        rlAssertNotExists "plans/example.fmf"
        rlRun -s "tmt init -t full"
        rlAssertGrep "Tree .* initialized." "${rlRun_LOG}"
        rlAssertGrep "Applying template 'full'." "${rlRun_LOG}"
        rlAssertGrep "Directory .* created." "${rlRun_LOG}"
        rlAssertExists "plans/example.fmf"
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd

rlJournalEnd
