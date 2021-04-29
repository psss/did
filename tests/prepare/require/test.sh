#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for image in fedora centos:7 ; do
        # Prepare the tmt command and expected error message
        tmt="tmt run -avr provision -h container -i $image"
        if [[ $image == fedora ]]; then
            error='Unable to find a match: forest'
        else
            error='No package forest available'
        fi

        rlPhaseStartTest "Require an available package ($image)"
            rlRun "$tmt plan --name available | tee output"
            rlAssertGrep '1 preparation applied' output
        rlPhaseEnd

        rlPhaseStartTest "Require a missing package ($image)"
            rlRun "$tmt plan --name missing | tee output" 2
            rlAssertGrep "$error" output
        rlPhaseEnd

        rlPhaseStartTest "Require both available and missing ($image)"
            rlRun "$tmt plan --name mixed | tee output" 2
            rlAssertGrep "$error" output
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm -f output"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
