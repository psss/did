#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

TMP_FILE="test_log_for_submitting.txt"
TMP_FILE_SRC_PATH="/tmp/$TMP_FILE"
TMP_FILE_DEST_PATH="$TMT_TEST_DATA/$TMP_FILE"

rlJournalStart
    rlPhaseStartSetup
        rlRun "touch $TMP_FILE_SRC_PATH" 0 "Test log file successfully created."
    rlPhaseEnd

    rlPhaseStartTest 'Verify mocked Restraint rstrnt-report-log correctly saves log file.'
        rlRun "tmt-file-submit -l $TMP_FILE_SRC_PATH" 0 "Saving log with tmt-file-submit."
        rlRun "ls $TMP_FILE_DEST_PATH" 0 "Checking log saved to expected destination."
        rlRun "rm -f $TMP_FILE_DEST_PATH" 0 "Removing log file."
        rlRun "rstrnt-report-log --server http://test-example.com --port 77 --filename $TMP_FILE_SRC_PATH" 0 "Saving log with rstrnt-report-log."
        rlRun "ls $TMP_FILE_DEST_PATH" 0 "Checking log saved to expected destination."
        rlRun "rm -f $TMP_FILE_DEST_PATH" 0 "Removing log file."
        rlRun "rhts-submit-log -T ignored --server http://test-example.com --port 77 --filename $TMP_FILE_SRC_PATH" 0 "Saving log with rhts-submit-log."
        rlRun "ls $TMP_FILE_DEST_PATH" 0 "Checking log saved to expected destination."
        rlRun "rm -f $TMP_FILE_DEST_PATH" 0 "Removing log file."
        rlRun "rhts_submit_log -T ignored --server http://test-example.com --port 77 --filename $TMP_FILE_SRC_PATH" 0 "Saving log with rhts_submit_log."
        rlRun "ls $TMP_FILE_DEST_PATH" 0 "Checking log saved to expected destination."
        rlRun "rm -f $TMP_FILE_DEST_PATH" 0 "Removing log file."
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -f $TMP_FILE_SRC_PATH" 0 "Test log file successfully removed."
    rlPhaseEnd
rlJournalEnd
