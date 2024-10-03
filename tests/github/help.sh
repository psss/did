#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest "Help"
        rlRun -s "did --config ./config-default.ini --help"
        rlAssertGrep "GitHub work" $rlRun_LOG
        for what in issues pull-requests; do
            for action in created commented closed; do
                rlAssertGrep "--gh-$what-$action" $rlRun_LOG
            done
        done
    rlPhaseEnd
rlJournalEnd
