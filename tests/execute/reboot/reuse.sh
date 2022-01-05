#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

trim() {
    sed -e 's/ *$//g' -e 's/^ *//g'
}

get_value() {
    grep "$1:" "$2" | cut -d':' -f2 | trim
}

rlJournalStart
    rlPhaseStartSetup
        rlRun "provision_run=\$(mktemp -d)" 0 "Create directory for provision run"
        # Must be outside /tmp, reboot would remove it otherwise
        rlRun "run=\$(mktemp -d -p /var/tmp/tmt)" 0 "Create run directory"
        rlRun "set -o pipefail"
        rlRun "pushd data"
    rlPhaseEnd

    rlPhaseStartTest "Reuse the same provision"
        rlRun "tmt run -i $provision_run provision -h virtual"
        guests="$provision_run/plan/provision/guests.yaml"
        guest=$(get_value "guest" "$guests")
        port=$(get_value "port" "$guests")
        user=$(get_value "user" "$guests")
        key=$(get_value "key" "$guests")
        provision="provision -h connect -g $guest -P $port -u $user -k $key"
        for _ in $(seq 0 1); do
            rlRun -s "tmt run --scratch -ai $run -dddvvv $provision"
            rlAssertGrep "Reboot during test '/test' with reboot count 1" $rlRun_LOG
            rlAssertGrep "After first reboot" $rlRun_LOG
            rlAssertGrep "Reboot during test '/test' with reboot count 2" $rlRun_LOG
            rlAssertGrep "After second reboot" $rlRun_LOG
            rlAssertGrep "Reboot during test '/test' with reboot count 3" $rlRun_LOG
            rlAssertGrep "After third reboot" $rlRun_LOG
            rlRun "rm $rlRun_LOG"

            # Check that the whole output log is kept
            rlRun "log=$run/plan/execute/data/test/output.txt"
            rlAssertGrep "After first reboot" $log
            rlAssertGrep "After second reboot" $log
            rlAssertGrep "After third reboot" $log
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "tmt run -i $provision_run finish"
        rlRun "rm -rf output $run $provision_run" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
