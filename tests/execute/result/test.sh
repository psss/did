#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

run()
{
    res=$1  # expected final result of test
    tn=$2   # test name
    orig=$3 # original result
    ret=$4  # tmt return code

    rlRun -s "tmt run -a --scratch --id \${run} test --name ${tn} provision --how local report -v | grep report -A2 | tail -n 1" \
        ${ret} "Result: ${res}, Test name: ${tn}, Original result: '${orig}', tmt return code: ${ret}"

    if [ -z "${orig}" ]; then # No original result provided
        rlAssertGrep "${res} ${tn}$" $rlRun_LOG
    else
        rlAssertGrep "${res} ${tn} (original result: ${orig})$" $rlRun_LOG
    fi

    echo
}

rlJournalStart
    rlPhaseStartSetup
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Running tests separately"
        ###   Table of expected results
        #
        #     result    test name            original  return
        #                                     result    code
        run   "pass"   "/test/pass"           ""         0
        run   "fail"   "/test/fail"           ""         1
        run   "errr"   "/test/error"          ""         2
        run   "pass"   "/test/xfail-fail"     "fail"     0
        run   "fail"   "/test/xfail-pass"     "pass"     1
        run   "errr"   "/test/xfail-error"    "error"    2
        run   "pass"   "/test/always-pass"    "fail"     0
        run   "info"   "/test/always-info"    "pass"     2
        run   "warn"   "/test/always-warn"    "pass"     1
        run   "fail"   "/test/always-fail"    "pass"     1
        run   "errr"   "/test/always-error"   "pass"     2
    rlPhaseEnd

    rlPhaseStartTest "Verbose execute prints result"
        rlRun -s "tmt run --id \${run} --scratch --until execute tests --filter tag:-cherry_pick provision --how local execute -v" "2"
        while read -r line; do
            if rlIsRHELLike "=8" && [[ $line =~ /test/error-timeout ]]; then
                # Centos stream 8 doesn't do watchdog properly https://github.com/teemtee/tmt/issues/1387
                # so we can't assert expected duration (1s) in /test/error-timeout
                # FIXME remove this once issue is fixed
                rlAssertGrep "errr /test/error-timeout (timeout) [7/12]" "$rlRun_LOG" -F
            else
                rlAssertGrep "$line" "$rlRun_LOG" -F
            fi
        done <<-EOF
00:00:00 errr /test/always-error (original result: pass) [1/12]
00:00:00 fail /test/always-fail (original result: pass) [2/12]
00:00:00 info /test/always-info (original result: pass) [3/12]
00:00:00 pass /test/always-pass (original result: fail) [4/12]
00:00:00 warn /test/always-warn (original result: pass) [5/12]
00:00:00 errr /test/error [6/12]
00:00:01 errr /test/error-timeout (timeout) [7/12]
00:00:00 fail /test/fail [8/12]
00:00:00 pass /test/pass [9/12]
00:00:00 errr /test/xfail-error (original result: error) [10/12]
00:00:00 pass /test/xfail-fail (original result: fail) [11/12]
00:00:00 fail /test/xfail-pass (original result: pass) [12/12]
EOF
    rlPhaseEnd

    rlPhaseStartTest "Verbose execute prints result - reboot case"
        # Before the reboot results is not known
        rlRun -s "tmt run --id \${run} --scratch --until execute tests -n /xfail-with-reboot provision --how container execute -v"
        EXPECTED=$(cat <<EOF
            00:00:00 /test/xfail-with-reboot [1/1]
            00:00:00 pass /test/xfail-with-reboot (original result: fail) [1/1]
EOF
)
    rlAssertEquals "Output matches the expectation" "$EXPECTED" "$(grep /test/xfail-with-reboot $rlRun_LOG)"
    rlPhaseEnd

    rlPhaseStartTest "Verbose execute prints result - abort case"
        rlRun -s "tmt run --id \${run} --scratch --until execute tests tests -n /abort provision --how container execute -v" "2"
        rlAssertGrep "00:00:00 errr /test/abort (aborted) [1/1" $rlRun_LOG -F
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r ${run}" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
