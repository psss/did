#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        python_cmd='import ruamel.yaml, sys; print(list(ruamel.yaml.YAML(typ=\"safe\").load_all(sys.stdin)))'
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "tmt tests export --fmf-id"
        rlRun "tmt tests export --fmf-id | python3 -c \"$python_cmd\" | tee $output"
        for test in $(tmt tests ls); do
            rlAssertGrep "$test" $output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
