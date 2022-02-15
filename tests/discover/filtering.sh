#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest "Filter by test name"
        plan='plan --name fmf/nourl/noref/nopath'
        discover='discover --how fmf --test discover1'
        rlRun 'tmt run -dvr $discover $plan finish | tee output'
        rlAssertGrep '1 test selected' output
        rlAssertGrep '/tests/discover1' output
        rlAssertNotGrep '/tests/discover2' output
        rlAssertNotGrep '/tests/discover3' output
    rlPhaseEnd

    rlPhaseStartTest "Filter by advanced filter"
        plan='plan --name fmf/nourl/noref/nopath'
        discover='discover --how fmf --filter tier:1,2'
        rlRun 'tmt run -dvr $discover $plan finish | tee output'
        rlAssertGrep '2 tests selected' output
        rlAssertGrep '/tests/discover1' output
        rlAssertGrep '/tests/discover2' output
        rlAssertNotGrep '/tests/discover3' output
    rlPhaseEnd

    rlPhaseStartTest "Filter by link"
        plan='plans --default'
        for link_relation in "" "relates:" "rel.*:"; do
            discover="discover -h fmf --link ${link_relation}/tmp/foo"
            rlRun 'tmt run -dvr $discover $plan finish | tee output'
            rlAssertGrep '1 test selected' output
            rlAssertGrep '/tests/discover1' output
        done
        for link_relation in "verifies:https://github.com/teemtee/tmt/issues/870" \
            "ver.*:.*/issues/870" ".*/issues/870"; do
            discover="discover -h fmf --link $link_relation --link rubbish"
            rlRun "tmt run -dvr $discover $plan finish | tee output"
            rlAssertGrep '1 test selected' output
            rlAssertGrep '/tests/discover2' output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
