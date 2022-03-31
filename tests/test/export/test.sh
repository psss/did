#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
        tnames="$(tmt tests ls)"
    rlPhaseEnd

    # 1 - (positive) format testing
    cmd="tmt tests export ."
    rlPhaseStartTest "$cmd"
        rlRun -s "$cmd | ../parse.py" 0 "Export test"
    rlPhaseEnd

    for tname in $tnames; do
        cmd="tmt tests export $tname"
        rlPhaseStartTest "$cmd"
            rlRun -s "$cmd" 0 "Export test"
            rlAssertGrep "- name: $tname" $rlRun_LOG
        rlPhaseEnd

        cmd="tmt tests export --format dict $tname"
        rlPhaseStartTest "$cmd"
            rlRun -s "$cmd" 0 "Export test"
            rlAssertGrep "'name': '$tname'" $rlRun_LOG
        rlPhaseEnd

        cmd="tmt tests export --format yaml $tname"
        rlPhaseStartTest "$cmd"
            rlRun -s "$cmd" 0 "Export test"
            rlAssertGrep "- name: $tname" $rlRun_LOG
        rlPhaseEnd
    done

    # 2 - (negative) format testing
    rlPhaseStartTest "Invalid format"
        rlRun -s "tmt tests export --format weird" 2
        rlAssertGrep "Invalid test export format" $rlRun_LOG
    rlPhaseEnd

    # 3 - fmf-id testing
    cmd="tmt tests export . --fmf-id"
    rlPhaseStartTest "$cmd"
        rlRun -s "$cmd" 0 "Export test"
        for tname in $tnames; do
            rlAssertGrep "- name: $tname" $rlRun_LOG
        done
    rlPhaseEnd

    for tname in $tnames; do
        cmd="tmt tests export --fmf-id $tname"
        rlPhaseStartTest "$cmd"
            rlRun -s "$cmd" 0 "Export test"
            rlAssertGrep "- name: $tname" $rlRun_LOG
        rlPhaseEnd

        cmd="tmt tests export --format dict --fmf-id $tname"
        rlPhaseStartTest "$cmd"
            rlRun -s "$cmd" 0 "Export test"
            rlAssertGrep "'name': '$tname'" $rlRun_LOG
        rlPhaseEnd

        cmd="tmt tests export --format yaml --fmf-id $tname"
        rlPhaseStartTest "$cmd"
            rlRun -s "$cmd" 0 "Export test"
            rlAssertGrep "- name: $tname" $rlRun_LOG
        rlPhaseEnd
    done

    rlPhaseStartTest "Test does not exist"
        rlRun -s "tmt tests export --format yaml --fmf-id XXX" 0
        rlAssertGrep "\[\]" $rlRun_LOG

        rlRun -s "tmt tests export --format dict --fmf-id XXX" 0
        rlAssertGrep "\[\]" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
