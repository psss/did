#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest 'Command-line'
        rlRun 'tmt run -dv discover --how fmf  --ref 8329db0421e9 \
            --modified-only --modified-ref 8329db0421e9^ \
            | tee output'
        rlAssertGrep 'summary: 1 test selected' output
        rlAssertGrep '/tests/core/adjust' output
    rlPhaseEnd

    rlPhaseStartTest 'Plan'
        rlRun 'env -C data tmt run -dv discover plan -n fmf/modified-only | tee output'
        rlAssertGrep 'summary: 1 test selected' output
        rlAssertGrep '/tests/core/adjust' output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'rm -f output' 0 'Removing tmp file'
    rlPhaseEnd
rlJournalEnd
