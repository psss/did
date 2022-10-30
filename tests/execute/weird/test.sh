#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    for executor in tmt; do
        rlPhaseStartTest "Test with the $executor executor"
            rlRun "tmt run -i $tmp/$executor -avvvddd \
                provision -h local \
                execute -h $executor 2>&1 >/dev/null | tee output"
            rlAssertGrep 'Before: This text is fine.' output
            rlAssertGrep 'Weird: That is the b.*d one!' output
            rlAssertGrep 'After: This text is fine as well.' output
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "rm output"
        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
