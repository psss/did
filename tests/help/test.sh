#!/bin/bash

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="did"

CONFIG="
[general]
email = email@example.com
"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TMP=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TMP"
        rlRun "echo $CONFIG > config"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "did --help --config $TMP/config | tee output" 0 "Check help"
        rlAssertGrep "week|month|quarter|year" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TMP" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
