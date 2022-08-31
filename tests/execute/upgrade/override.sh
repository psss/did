#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
        rlRun "run=/var/tmp/tmt/run-upgrade"
    rlPhaseEnd

    # Test that plan conditions are not applied to the remote repo
    # If it was applied, the second condition would prevent selection
    # of a plan, resulting in a failure.
    for condition in 'True' '"Basic upgrade test" in summary'; do
        rlPhaseStartTest "Plan condition $condition"
            rlRun -s "tmt run --scratch -avvvdddi $run --rm --before finish \
                plan -n /plan/path -c '$condition' \
                execute -h upgrade -F 'path:/tasks/prepare' \
                provision -h container -i fedora:35" 0 "Run a single upgrade task"
            # 1 test before + 1 upgrade tasks + 1 test after
            rlAssertGrep "3 tests passed" $rlRun_LOG
            # Check that the IN_PLACE_UPGRADE variable was set
            data="$run/plan/path/execute/data"
            rlAssertGrep "IN_PLACE_UPGRADE=old" "$data/old/test/output.txt"
            rlAssertGrep "IN_PLACE_UPGRADE=new" "$data/new/test/output.txt"
            # Environment of plan was passed
            rlAssertGrep "VERSION_ID=35" "$data/upgrade/tasks/prepare/output.txt"
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "tmt run -l finish" 0 "Stop the guest and remove the workdir"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd