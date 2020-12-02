#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

packages="did tree"
libraries="epel/epel example/file"

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "set -o pipefail"
        rlRun "pushd $tmp"
        rlRun rlGetMakefileRequires 1 "There should be no Makefile"
    rlPhaseEnd

    rlPhaseStartTest "Import all libraries"
        rlRun "rlImport --all 2>&1 | tee output"
        for library in $libraries; do
            rlAssertGrep "try to import $library" output
        done
    rlPhaseEnd

    rlPhaseStartTest "Check required packages"
        rlRun "rlCheckMakefileRequires 2>&1 | tee output"
        for package in $packages; do
            rlAssertGrep $package output
        done
    rlPhaseEnd

    rlPhaseStartTest "Assert required packages"
        rlRun "rlAssertRequired 2>&1 | tee output"
        for package in $packages; do
            rlAssertGrep $package output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
