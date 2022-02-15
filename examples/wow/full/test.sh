#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "run=/var/tmp/tmt/mini"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest
        # Install tmt, start libvirtd, clone report and look around
        rlRun "dnf install -y tmt-all" 0 "Install the full tmt package"
        rlRun "systemctl start libvirtd" 0 "Start libvirtd"
        rlRun "git clone https://github.com/teemtee/tmt"
        rlRun "pushd tmt"
        rlRun "tmt" 0 "Explore the repo"

        # Run tests with disabled reporting for included beakerlib tests
        report="$BEAKERLIB_COMMAND_REPORT_RESULT"
        export BEAKERLIB_COMMAND_REPORT_RESULT=/bin/true
        rlRun "tmt run -i $run -av \
            prepare -h install -c psss/tmt -p tmt-all \
            plan --name 'plans|container|virtual'"
        export BEAKERLIB_COMMAND_REPORT_RESULT="$report"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd; popd"
        rlBundleLogs workdir "$run"
        rlRun "rm -rf $tmp $run" 0 "Remove tmp directories"
    rlPhaseEnd
rlJournalEnd
