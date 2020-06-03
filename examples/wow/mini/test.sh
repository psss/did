#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "run=/var/tmp/tmt/mini"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "dnf install -y tmt" 0 "Install the base tmt package"
        rlRun "tmt init -t base" 0 "Initialize with the base template"
        rlRun "tmt run -i $run -av provision -h local" 0 "Run the example"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlBundleLogs workdir "$run"
        rlRun "rm -rf $tmp $run" 0 "Remove tmp directories"
    rlPhaseEnd
rlJournalEnd
