#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'pushd data'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest 'fmf help'
        rlRun 'tmt run discover --help --how fmf | tee output'
        rlAssertGrep 'Discover available tests from fmf metadata' 'output'
        for option in url ref path test filter fmf-id; do
            rlAssertGrep "--$option" output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
