#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Show tests"
        # Default context
        rlRun "tmt test show pidof | tee $output"
        rlAssertGrep 'enabled\s+true' $output -E
        # Fedora 33 (enabled)
        rlRun "tmt -c distro=fedora-33 test show pidof | tee $output"
        rlAssertGrep 'enabled\s+true' $output -E
        # CentOS 8 (enabled)
        rlRun "tmt -c distro=centos-8 test show pidof | tee $output"
        rlAssertGrep 'enabled\s+true' $output -E
        # CentOS 7 (disabled)
        rlRun "tmt -c distro=centos-7 test show pidof | tee $output"
        rlAssertGrep 'enabled\s+false' $output -E
        # Context file (pidof disabled, uptime duration adjusted)
        rlRun "tmt -c @context.yaml test show pidof | tee $output"
        rlAssertGrep 'enabled\s+false' $output -E
        rlRun "tmt -c @context.yaml test show uptime | tee $output"
        rlAssertGrep 'duration\s+1m' $output -E
    rlPhaseEnd

    rlPhaseStartTest "Show plans"
        # CentOS 7 (procps-ng)
        rlRun "tmt -c distro=centos-7 plan show centos-7 | tee $output"
        rlAssertGrep '^\s*package\s+procps-ng$' $output -E
        # CentOS 6 (procps-ng)
        rlRun "tmt -c distro=centos-6 plan show centos-6 | tee $output"
        rlAssertGrep '^\s*package\s+procps$' $output -E
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
