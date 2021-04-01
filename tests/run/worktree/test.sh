#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest "Simple"
        rlRun "pushd data/simple"
        rlRun "tmt run -ar report -vvv"
        rlRun "popd"
    rlPhaseEnd

    rlPhaseStartTest "Ansible"
        rlRun "pushd data/ansible"
        rlRun "tmt run -ar report -vvv"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
