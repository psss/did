#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    opt="-i $run --scratch provision prepare -vvv finish"
    rlPhaseStartTest "Run on all guests"
        rlRun -s "tmt run $opt plan -n all"
        # 4 implicit + 4 preparations run on all guests = 8 preparations
        rlAssertGrep "8 preparations applied" $rlRun_LOG
        rlRun "grep 'script: echo' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "4" lines
    rlPhaseEnd

    rlPhaseStartTest "Run on a single guest"
        rlRun -s "tmt run $opt plan -n name"
        # 4 implicit + 1 specific preparation = 5 preparations
        rlAssertGrep "5 preparations applied" $rlRun_LOG
        rlAssertGrep "where: server-one" $rlRun_LOG
        rlRun "grep 'script: echo' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "1" lines
    rlPhaseEnd

    rlPhaseStartTest "Run on all guests with a role"
        rlRun -s "tmt run $opt plan -n role"
        # 4 implicit + 2 run based on role = 6 preparations
        rlAssertGrep "6 preparations applied" $rlRun_LOG
        rlAssertGrep "where: server" $rlRun_LOG
        rlRun "grep 'script: echo' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "2" lines
    rlPhaseEnd

    rlPhaseStartTest "Combined case"
        rlRun -s "tmt run $opt plan -n combined"
        # 1 ran on all (4 guests) + 1 ran on server role (2 guests) + 1 ran
        # on single guest (1 guest) + 4 implicit preparations = 11 preparations
        rlAssertGrep "11 preparations applied" $rlRun_LOG
        rlRun "grep 'All' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "4" lines
        rlRun "grep 'Server' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "2" lines
        rlRun "grep 'Client one' $rlRun_LOG | wc -l > lines"
        rlAssertGrep "1" lines
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm lines"
        rlRun "popd"
        rlRun "rm -r $run" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
