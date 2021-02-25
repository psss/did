#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
    rlPhaseEnd

    for method in shell.tmt shell.detach; do
        rlPhaseStartTest "Test $method"
            rlRun "tmt run -vfi $tmp -a execute -h $method test --name good" 0
            rlRun "tmt run -vfi $tmp -a execute -h $method test --name long" 2
            rlRun "tmt run -vfi $tmp -a execute -h $method test --name beakerlib" 2
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
