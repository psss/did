#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        python_cmd='import yaml, sys; print(list(yaml.load_all(sys.stdin, Loader=yaml.FullLoader)))'
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "tmt tests export --fmf-id | python -c \"$python_cmd\" | tee $output"
    rlPhaseEnd

    rlPhaseStartTest "tmt tests export --fmf-id"
        for test in $(tmt tests ls); do
            rlAssertGrep "$test" $output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
