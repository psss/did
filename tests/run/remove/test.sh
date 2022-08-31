#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "run=\$(mktemp -d)" 0 "Creating run directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest "All steps at once (don't remove)"
        rlRun "tmt run --id $run --all \
            provision --how local \
            execute --how tmt --script true"
        rlAssertExists $run
    rlPhaseEnd

    rlPhaseStartTest "All steps at once (remove)"
        rlRun "tmt run --id $run --all --remove \
            provision --how local \
            execute --how tmt --script true"
        rlAssertNotExists $run
    rlPhaseEnd

    rlPhaseStartTest "Selected steps (remove)"
        rlRun "tmt run --id $run --remove \
            discover \
            provision --how local \
            execute --how tmt --script true"
        rlAssertExists $run
        rlRun "tmt run --last report"
        rlAssertExists $run
        rlRun "tmt run --last finish"
        rlAssertNotExists $run
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
