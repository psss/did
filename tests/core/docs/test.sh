#!/bin/bash

# Include Beaker environment
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="tmt"
EXAMPLES="/usr/share/doc/tmt/examples"

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm $PACKAGE
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "version"
        rlRun "tmt --version | tee output" 0 "Check version"
        rlAssertGrep "tmt version:" "output"
    rlPhaseEnd

    rlPhaseStartTest "help"
        rlRun "tmt --help | tee help" 0 "Run help"
        rlAssertGrep "Test Management Tool" "help"
    rlPhaseEnd

    rlPhaseStartTest "man"
        rlRun "man tmt | tee man" 0 "Check man page"
        rlAssertGrep "usage is straightforward" "man"
        rlAssertNotGrep "WARNING" "man"
    rlPhaseEnd

    rlPhaseStartTest "examples"
        rlRun "ls $EXAMPLES | tee examples" 0 "Check examples"
        rlAssertGrep "mini" "examples"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
