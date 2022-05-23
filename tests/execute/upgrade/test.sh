#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
        rlRun "run=/var/tmp/tmt/run-upgrade"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun -s "tmt run -vvvdddi $run --rm --before finish" 0 "Run the upgrade test"
        # 1 test before + 3 upgrade tasks + 1 test after
        rlAssertGrep "5 tests passed" $rlRun_LOG
        # Check that the IN_PLACE_UPGRADE variable was set
        rlAssertGrep "echo old" "$run/plan/execute/data/old/test/output.txt"
        rlAssertGrep "echo new" "$run/plan/execute/data/new/test/output.txt"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "tmt run -l finish" 0 "Stop the guest and remove the workdir"
    rlPhaseEnd
rlJournalEnd
