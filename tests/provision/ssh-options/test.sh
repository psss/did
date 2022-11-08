#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

METHODS=${METHODS:-virtual}

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
    rlPhaseEnd

    for provision_method in $METHODS; do
        rlPhaseStartTest "Test with provision $provision_method"
            rlRun "tmt run --scratch -vvi $run -a provision -h $provision_method --ssh-option ServerAliveCountMax=123456789"
            rlAssertGrep "Run command: ssh .*-oServerAliveCountMax=123456789" "$run/log.txt"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
