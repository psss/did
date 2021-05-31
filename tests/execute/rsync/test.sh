#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartTest "Test with rsync removed during execute"
        rlRun "tmt run -avvvddd \
            provision -h virtual \
            execute -h tmt -s 'rpm -e --nodeps rsync'"
    rlPhaseEnd
rlJournalEnd
