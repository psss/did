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
        rlAssertGrep 'enabled\s+yes' $output -E
        # CentOS 6 (disabled)
        rlRun "tmt -c distro=centos-6 test show pidof | tee $output"
        rlAssertGrep 'enabled\s+no' $output -E
        # Context file (pidof disabled, uptime duration adjusted)
        rlRun "tmt -c @context.yaml test show pidof | tee $output"
        rlAssertGrep 'enabled\s+no' $output -E
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

    rlPhaseStartTest "Fedora"
        rlRun "tmt -c distro=fedora run -arv plan --name fedora \
            2>&1 | tee $output"
        rlAssertGrep '3 tests passed' $output
        rlAssertGrep '^\s*procps-ng$' $output -E
        rlAssertGrep 'pidof' $output
    rlPhaseEnd

    rlPhaseStartTest "CentOS 8"
        rlRun "tmt -c distro=centos-8 run -arv plan --name centos-8 \
            2>&1 | tee $output"
        rlAssertGrep '3 tests passed' $output
        rlAssertGrep '^\s*procps-ng$' $output -E
        rlAssertGrep 'pidof' $output
    rlPhaseEnd

    rlPhaseStartTest "CentOS 7"
        rlRun "tmt -c distro=centos-7 run -arv plan --name centos-7 \
            2>&1 | tee $output"
        rlAssertGrep '2 tests passed' $output
        rlAssertGrep '^\s*procps-ng$' $output -E
        rlAssertNotGrep 'pidof' $output
    rlPhaseEnd

    rlPhaseStartTest "CentOS 6"
        rlRun "tmt -c distro=centos-6 run -arv plan --name centos-6 \
            2>&1 | tee $output"
        rlAssertGrep '2 tests passed' $output
        rlAssertGrep '^\s*procps$' $output -E
        rlAssertNotGrep 'pidof' $output
    rlPhaseEnd

    rlPhaseStartTest "Context from file"
        rlRun "tmt -c @context.yaml run -arv plan --name centos-6 \
            2>&1 | tee $output"
        rlAssertGrep '2 tests passed' $output
        rlAssertGrep '^\s*procps$' $output -E
        rlAssertNotGrep 'pidof' $output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
