#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt run -vfi $tmp -a provision -h container"
        FILE_PATH=$tmp/plans/default/execute/data/submitted/this_file.txt
        BUNDLE_PATH=$tmp/plans/default/execute/data/submitted/tmp-bundle_name.tar.gz

        # File was submitted and has correct content
        rlAssertExists $FILE_PATH
        rlAssertGrep "YES" $FILE_PATH

        # Bundle was submitted and has correct content
        rlAssertExists $BUNDLE_PATH
        rlRun "tar tzf $BUNDLE_PATH | grep /this_file.txt" \
            0 "Bundle contains an expected file"

        # FIXME - Present this information somehow to the user
        # (that they have some files...)
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
