#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "workdir=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "cp -r data $workdir"
        rlRun "pushd $workdir/data"
    rlPhaseEnd

    plan="plans --default"
    test_yaml="$workdir/run/plans/default/discover/tests.yaml"

    rlPhaseStartTest
        # Fresh run with no required packages
        rlRun -s "tmt run --id $workdir/run $plan discover -fv"
        rlAssertGrep " 3 tests selected" "$rlRun_LOG" -F
        rlAssertNotGrep "unique-package-name-foo" "$test_yaml" -F

        # Add a new require to the tests
        echo 'require: [unique-package-name-foo]' >> tests.fmf

        # Force run should discover new require
        rlRun -s "tmt run --id $workdir/run $plan discover -fv"
        rlAssertGrep " 3 tests selected" "$rlRun_LOG" -F
        rlAssertGrep "unique-package-name-foo" "$test_yaml" -F
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'popd'
        rlRun "rm -rf $workdir" 0 'Remove tmp directory'
    rlPhaseEnd
rlJournalEnd
