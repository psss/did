#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd custom"
        rlRun "set -o pipefail"
        rlRun "run=\$(mktemp -d)" 0 "Creating run direcotory/id"
    rlPhaseEnd

    tmt_command="tmt run --scratch -a --id ${run} provision --how local execute -vv report -vv test --name"

    testName="/test/custom-results"
    rlPhaseStartTest "${testName}"
        rlRun -s "${tmt_command} ${testName}" 1 "Test provides 'results.yaml' file by itself"
        rlAssertGrep "00:11:22 pass /test/custom-results/test/passing" $rlRun_LOG
        rlAssertGrep "00:22:33 fail /test/custom-results/test/failing" $rlRun_LOG
        rlAssertGrep "         pass /test/custom-results/test/no_keys \[1/1\]" $rlRun_LOG
        rlAssertGrep "total: 2 tests passed and 1 test failed" $rlRun_LOG
    rlPhaseEnd

    testName="/test/missing-custom-results"
    rlPhaseStartTest "${testName}"
        rlRun -s "${tmt_command} ${testName}" 2 "Test does not provide 'results.yaml' file"
        rlAssertGrep "custom results file '/tmp/.*/plans/default/execute/data/test/missing-custom-results/data/results.yaml' not found" $rlRun_LOG
    rlPhaseEnd

    testName="/test/empty-custom-results-file"
    rlPhaseStartTest "${testName}"
        rlRun -s "${tmt_command} ${testName}" 3 "Test provides empty 'results.yaml' file"
        rlAssertGrep "total: no results found" $rlRun_LOG
    rlPhaseEnd

    testName="/test/wrong-yaml-results-file"
    rlPhaseStartTest "${testName}"
        rlRun -s "${tmt_command} ${testName}" 2 "Test provides 'results.yaml' in valid YAML but wrong results format"
        rlAssertGrep "Expected list in yaml data, got 'dict'." $rlRun_LOG
    rlPhaseEnd

    testName="/test/invalid-yaml-results-file"
    rlPhaseStartTest "${testName}"
        rlRun -s "${tmt_command} ${testName}" 2 "Test provides 'results.yaml' not in YAML format"
        rlAssertGrep "Invalid yaml syntax:" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -r ${run}" 0 "Remove run directory"
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
