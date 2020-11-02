#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "tmt run -vi $tmp"
        metadata="$tmp/plan/execute/data/test/metadata.yaml"
        rlRun "cat $metadata" 0 "Check metadata.yaml content"
        rlAssertGrep "name: /test" $metadata
        rlAssertGrep "summary: Simple test" $metadata
        rlAssertGrep "library(epel/epel)" $metadata
        rlAssertGrep "weather: nice" $metadata
        rlAssertGrep "duration: 5m" $metadata
        rlRun "grep -A1 recommend $metadata | grep forest" \
            0 "Recommend should be converted to a list"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
