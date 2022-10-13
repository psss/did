#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Plan with a good context"
        rlRun -s "tmt -c distro=rhel9 -c arch=aarch64,x86_64 plan show good"
        rlAssertGrep "foo: \['bar'\]" $rlRun_LOG
        rlAssertGrep "baz: \['qux', 'fred'\]" $rlRun_LOG
        rlAssertGrep "distro: \['rhel9'\]" $rlRun_LOG
        rlAssertGrep "arch: \['aarch64', 'x86_64'\]" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Plan with a bad context"
        rlRun -s "tmt -c distro=rhel9 -c arch=aarch64,x86_64 plan show bad"
        rlAssertGrep "distro: \['rhel9'\]" $rlRun_LOG
        rlAssertGrep "arch: \['aarch64', 'x86_64'\]" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Plan with a good context, overwritten by command line"
        rlRun -s "tmt -c distro=rhel9 -c arch=aarch64,x86_64 -c baz=something,different plan show good"
        rlAssertGrep "foo: \['bar'\]" $rlRun_LOG
        rlAssertGrep "baz: \['something', 'different'\]" $rlRun_LOG
        rlAssertGrep "distro: \['rhel9'\]" $rlRun_LOG
        rlAssertGrep "arch: \['aarch64', 'x86_64'\]" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Plan with broken values"
        rlRun -s "tmt -c distro=rhel9 -c arch=aarch64,x86_64 plan show bad-values"
        cp $rlRun_LOG /tmp/tmp.txt
        rlAssertGrep "foo: \['foo'\]" $rlRun_LOG
        rlAssertGrep "bar: \['1'\]" $rlRun_LOG
        rlAssertGrep "baz: \['False'\]" $rlRun_LOG
        rlAssertGrep "distro: \['rhel9'\]" $rlRun_LOG
        rlAssertGrep "arch: \['aarch64', 'x86_64'\]" $rlRun_LOG
        rlAssertGrep "warn: /bad-values:context.baz - False is not valid under any of the given schemas" $rlRun_LOG
        rlAssertGrep "warn: /bad-values:context.dud - {'how': 'about'} is not valid under any of the given schemas" $rlRun_LOG
        rlAssertGrep "warn: /bad-values:context.bar - 1 is not valid under any of the given schemas" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
