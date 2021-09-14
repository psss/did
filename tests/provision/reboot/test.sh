#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

METHODS=${METHODS:-container}

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
        rlRun "tmt plan create -t mini plan"
    rlPhaseEnd

    if [[ "$METHODS" =~ container ]]; then
        rlPhaseStartTest "Container"
            rlRun "tmt run -i $run provision -h container"

            rlRun "tmt run -l reboot" 2 "Containers do not support soft reboot"
            rlRun -s "tmt run -l reboot --hard"
            rlAssertGrep "Reboot finished" $rlRun_LOG
            rlRun "rm $rlRun_LOG"
            rlRun "tmt run -l finish"
        rlPhaseEnd
    fi

    if [[ "$METHODS" =~ virtual ]]; then
        rlPhaseStartTest "Virtual"
            rlRun "tmt run --scratch -i $run provision -h virtual"

            rlRun -s "tmt run -l reboot"
            rlAssertGrep "Reboot finished" $rlRun_LOG
            rlRun "rm $rlRun_LOG"

            rlRun -s "tmt run -l reboot --hard"
            rlAssertGrep "Reboot finished" $rlRun_LOG
            rlRun "rm $rlRun_LOG"

            rlRun "tmt run -l finish"
        rlPhaseEnd
    fi

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
