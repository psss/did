#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1
ABORT_FILE="abort"
ABORT_FILE_PATH="$TMT_TEST_DATA/$ABORT_FILE"

rlJournalStart
    rlPhaseStartTest 'Verify abort file.'
        rlRun "tmt-abort" 0 "Aborting with tmt-abort."
        rlRun "echo \"This test should not be executed.\""
    rlPhaseEnd
rlJournalEnd
