#!/bin/bash
. /usr/lib/beakerlib/beakerlib.sh || exit 1
. /usr/share/rhts-library/rhtslib.sh || exit 1
. /usr/bin/rhts-environment.sh || exit 1

rlJournalStart
    rlPhaseStartTest
        rlRun "true" 0 "Everything's fine."
    rlPhaseEnd
rlJournalEnd
