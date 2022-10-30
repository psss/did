#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup "Prepare library"
        rlRun "libdir=\$(mktemp -d)" 0 "Create libdir directory"
        rlRun "pushd $libdir"
        rlRun "git clone https://github.com/beakerlib/example"
        rlRun "sed -i 's/Creating file/Create fyle/' example/file/lib.sh"
        rlRun "popd"
    rlPhaseEnd

    rlPhaseStartSetup "Prepare test"
        rlRun "testdir=\$(mktemp -d)" 0 "Create testdir directory"
        rlRun "cp -a data $testdir"
        rlRun "pushd $testdir/data"
        rlRun "sed -i 's|PATH|${libdir}/example|' main.fmf"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "set -o pipefail"
        rlRun "tmt run -ar discover -vvvddd report -vvv 2>&1 >/dev/null | tee output"
        rlAssertGrep "Copy local library.*example" "output"
        rlAssertGrep "Create fyle 'fooo'" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $libdir $testdir" 0 "Remove temporary directories"
    rlPhaseEnd
rlJournalEnd
