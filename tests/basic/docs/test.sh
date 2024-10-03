#!/bin/bash
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
        rlRun "echo '$CONFIG' > config"
    rlPhaseEnd

    rlPhaseStartTest "help"
        rlRun "did --help --config $TMP/config | tee help" 0 "Check help"
        rlAssertGrep "What did you do last week, month, year?" "help"
    rlPhaseEnd

    rlPhaseStartTest "man"
        rlRun "man did | tee man" 0 "Check man page"
        rlAssertGrep "What did you do last week, month, year?" "man"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TMP" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
