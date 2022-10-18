#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    for method in ${METHODS:-local}; do
        rlPhaseStartTest "With $method provision method"
            rlRun -s "tmt run -avvvvddd provision -h $method"

            rlAssertGrep "out: prepare: stdin: False" $rlRun_LOG
            rlAssertGrep "out: prepare: stdout: False" $rlRun_LOG
            rlAssertGrep "out: prepare: stderr: False" $rlRun_LOG

            rlAssertGrep "out: execute: stdin: False" $rlRun_LOG
            rlAssertGrep "out: execute: stdout: False" $rlRun_LOG
            rlAssertGrep "out: execute: stderr: False" $rlRun_LOG

            rlAssertGrep "out: finish: stdin: False" $rlRun_LOG
            rlAssertGrep "out: finish: stdout: False" $rlRun_LOG
            rlAssertGrep "out: finish: stderr: False" $rlRun_LOG

            rlAssertGrep "out: prepare: stdin: 0" $rlRun_LOG
            rlAssertGrep "out: prepare: stdout: 0" $rlRun_LOG
            rlAssertGrep "out: prepare: stderr: 0" $rlRun_LOG

            rlAssertGrep "out: execute: stdin: 0" $rlRun_LOG
            rlAssertGrep "out: execute: stdout: 0" $rlRun_LOG
            rlAssertGrep "out: execute: stderr: 0" $rlRun_LOG

            rlAssertGrep "out: finish: stdin: 0" $rlRun_LOG
            rlAssertGrep "out: finish: stdout: 0" $rlRun_LOG
            rlAssertGrep "out: finish: stderr: 0" $rlRun_LOG
        rlPhaseEnd

        rlPhaseStartTest "With $method provision method, interactive tests"
            rlRun -s "NO_COLOR=1 ../ptty-wrapper tmt run -avvvvddd provision -h $method execute -h tmt --interactive"

            rlAssertGrep "out: prepare: stdin: False" $rlRun_LOG
            rlAssertGrep "out: prepare: stdout: False" $rlRun_LOG
            rlAssertGrep "out: prepare: stderr: False" $rlRun_LOG

            rlAssertGrep "execute: stdin: True" $rlRun_LOG
            rlAssertGrep "execute: stdout: True" $rlRun_LOG
            rlAssertGrep "execute: stderr: True" $rlRun_LOG

            rlAssertGrep "out: finish: stdin: False" $rlRun_LOG
            rlAssertGrep "out: finish: stdout: False" $rlRun_LOG
            rlAssertGrep "out: finish: stderr: False" $rlRun_LOG

            rlAssertGrep "out: prepare: stdin: 0" $rlRun_LOG
            rlAssertGrep "out: prepare: stdout: 0" $rlRun_LOG
            rlAssertGrep "out: prepare: stderr: 0" $rlRun_LOG

            rlAssertGrep "execute: stdin: 1" $rlRun_LOG
            rlAssertGrep "execute: stdout: 1" $rlRun_LOG
            rlAssertGrep "execute: stderr: 1" $rlRun_LOG

            rlAssertGrep "out: finish: stdin: 0" $rlRun_LOG
            rlAssertGrep "out: finish: stdout: 0" $rlRun_LOG
            rlAssertGrep "out: finish: stderr: 0" $rlRun_LOG
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
