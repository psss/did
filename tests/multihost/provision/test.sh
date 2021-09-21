#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    opt="--scratch -i $run"
    rlPhaseStartTest "Wrong provision"
        rlRun -s "tmt run $opt plan -n wrong provision finish" \
            2 "Names not unique"
        rlAssertGrep "must be unique" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Correct provision without roles"
        rlRun -s "tmt run $opt plan -n noroles provision finish" 0
        rlAssertGrep "2 guests provisioned" $rlRun_LOG
        # how: container should be there twice
        rlRun "grep 'how: container' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "2" lines

        # 2 guests without role are saved
        guests="$run/noroles/provision/guests.yaml"
        rlAssertNotGrep "role" $guests
        rlAssertGrep "client" $guests
        rlAssertGrep "server" $guests

        # 2 guests were removed
        rlRun "grep 'container: removed' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "2" lines

        rlRun "rm lines"
    rlPhaseEnd

    rlPhaseStartTest "Correct provision with roles"
        rlRun -s "tmt run $opt plan -n /roles provision finish" 0
        rlAssertGrep "4 guests provisioned" $rlRun_LOG
        # how: container should be there 4 times
        rlRun "grep 'how: container' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "4" lines

        guests="$run/roles/provision/guests.yaml"
        rlAssertGrep "client-one" $guests
        rlAssertGrep "client-two" $guests
        rlAssertGrep "server-one" $guests
        rlAssertGrep "server-two" $guests

        # Each guest has a role
        rlRun "grep 'role: ' $guests | wc -l > lines"
        rlAssertGrep "4" "lines"

        # 4 guests were removed
        rlRun "grep 'container: removed' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "4" lines

        rlRun "rm lines"
    rlPhaseEnd

    rlPhaseStartTest "Full plan without roles"
        rlRun -s "tmt run $opt plan -n noroles"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
