#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory for failed run"
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    plan=fmf/nourl/noref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dvr discover plan --name $plan finish 2>&1 >/dev/null | tee output'
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
        rlRun 'tmt run -dvr discover --how fmf --path $path plan --name $plan \
            finish 2>&1 >/dev/null | tee output'
        rlAssertNotGrep 'Cloning into' output
        rlAssertNotGrep 'Checkout ref' output
        rlAssertGrep '3 tests selected' output
        rlAssertGrep /tests/discover1 output
        rlAssertGrep /tests/discover2 output
        rlAssertGrep /tests/discover3 output
    rlPhaseEnd

    plan=fmf/nourl/ref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dvr discover plan --name $plan finish 2>&1 >/dev/null | tee output'
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
        rlRun 'tmt run -dddvr discover --how fmf --path $path \
            plan --name $plan finish 2>&1 >/dev/null | tee output'
        rlAssertNotGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*eae4d52' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/full output
        rlAssertGrep /tests/smoke output
    rlPhaseEnd

    plan=fmf/url/noref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddvr discover plan --name $plan finish 2>&1 >/dev/null | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertNotGrep 'Checkout ref.*main' output
        rlAssertGrep /tests/core/docs output
        rlAssertGrep /tests/core/env output
        rlAssertGrep /tests/core/ls output
    rlPhaseEnd

    plan=fmf/url/noref/path
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddvr discover plan --name $plan finish 2>&1 >/dev/null | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertNotGrep 'Checkout ref.*main' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/full output
        rlAssertGrep /tests/smoke output
    rlPhaseEnd

    plan=fmf/url/ref/nopath
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddvr discover plan --name $plan finish 2>&1 >/dev/null | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*5407fe5' output
        rlAssertGrep 'hash.*5407fe5' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/docs output
        rlAssertNotGrep /tests/env output
        rlAssertGrep /tests/ls output
    rlPhaseEnd

    plan=fmf/url/ref/path
    rlPhaseStartTest $plan
        rlRun 'tmt run -dddvr discover plan --name $plan finish 2>&1 >/dev/null | tee output'
        rlAssertGrep 'Cloning into' output
        rlAssertGrep 'Checkout ref.*eae4d52' output
        rlAssertGrep 'hash.*eae4d52' output
        rlAssertGrep '2 tests selected' output
        rlAssertGrep /tests/full output
        rlAssertGrep /tests/smoke output
        # Before the change was committed
        rlRun "tmt run -i $tmp -d discover --how fmf --ref eae4d52^ plan \
            --name $plan 2>&1 >/dev/null | tee output" 2
        rlAssertGrep 'Metadata tree path .* not found.' output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
