#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    plan=fmf/nourl/noref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dv discover plan --name $plan | tee output'
        rlAssertNotGrep 'Cloning into' output
        rlAssertNotGrep 'Checkout ref' output
        rlAssertGrep '3 tests selected' output
        rlAssertGrep /tests/discover1 output
        rlAssertGrep /tests/discover2 output
        rlAssertGrep /tests/discover3 output
    rlPhaseEnd

    plan=fmf/nourl/noref/path
    path=$(realpath .)
    rlPhaseStartTest $plan
        rlRun 'tmt run -dv discover --how fmf --path $path plan --name $plan \
            | tee output'
        rlAssertNotGrep 'Cloning into' output
        rlAssertNotGrep 'Checkout ref' output
        rlAssertGrep '3 tests selected' output
        rlAssertGrep /tests/discover1 output
        rlAssertGrep /tests/discover2 output
        rlAssertGrep /tests/discover3 output
    rlPhaseEnd

    plan=fmf/nourl/ref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dv discover plan --name $plan | tee output'
        rlAssertNotGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*5407fe5' output
        rlAssertGrep /tests/docs output
        rlAssertNotGrep /tests/env output
        rlAssertGrep /tests/ls output
    rlPhaseEnd

    plan=fmf/nourl/ref/path
    path=$(realpath ../../../examples/together)
    echo $path
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddv discover --how fmf --path $path \
            plan --name $plan | tee output'
        rlAssertNotGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*eae4d52' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/full output
        rlAssertGrep /tests/smoke output
    rlPhaseEnd

    plan=fmf/url/noref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddv discover plan --name $plan | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*master' output
        rlAssertGrep /tests/core/docs output
        rlAssertGrep /tests/core/env output
        rlAssertGrep /tests/core/ls output
    rlPhaseEnd

    plan=fmf/url/noref/path
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddv discover plan --name $plan | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*master' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/full output
        rlAssertGrep /tests/smoke output
    rlPhaseEnd

    plan=fmf/url/ref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddv discover plan --name $plan | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*5407fe5' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/docs output
        rlAssertNotGrep /tests/env output
        rlAssertGrep /tests/ls output
    rlPhaseEnd

    plan=fmf/url/ref/path
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddv discover plan --name $plan | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*eae4d52' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/full output
        rlAssertGrep /tests/smoke output
        # Before the change was committed
        rlRun 'tmt run -d discover --how fmf --ref eae4d52^ plan --name $plan \
            2>&1 | tee output' 2
        rlAssertGrep 'Metadata tree path .* not found.' output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
