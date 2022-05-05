#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

METHODS=${METHODS:-container}

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd $tmp"
        rlRun "set -o pipefail"
        rlRun "tmt init"
        STEPS="--execute 'script: id'"
        rlRun "tmt plan create test --template mini $STEPS"
    rlPhaseEnd

    if [[ "$METHODS" =~ container ]]; then
        rlPhaseStartTest "Container, default user root"
            rlRun -s "tmt run -i $run -a provision -h container report -vvv"
            rlAssertGrep "uid=0(root) gid=0(root) groups=0(root)" $rlRun_LOG
        rlPhaseEnd

        rlPhaseStartTest "Container, set specific user"
            rlRun -s "tmt run --scratch -i $run -a provision -h container -u nobody report -vvv"
            rlAssertGrep "uid=65534(nobody) gid=65534(nobody) groups=65534(nobody)" $rlRun_LOG
        rlPhaseEnd
    fi

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
