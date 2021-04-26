#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    for image in fedora centos:7 centos:8; do
        rlPhaseStartTest $image
            rlRun "tmt run -arv provision -h container -i $image"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
