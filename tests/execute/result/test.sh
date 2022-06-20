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

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r ${run}" 0 "Remove run directory"
    rlPhaseEnd
rlJournalEnd
