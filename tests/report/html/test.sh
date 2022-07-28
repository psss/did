#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
        rlRun "set -o pipefail"
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
    rlPhaseEnd

    for method in tmt; do
        rlPhaseStartTest "$method"

            run_dir="$tmp/$method"
            rlRun "mkdir -p $tmp/$method"

            rlRun "tmt run -av --scratch --id $run_dir execute -h $method report -h html | tee output" 2
            rlAssertGrep "summary: 2 tests passed, 1 test failed and 2 errors" output -F

            HTML="$run_dir/plan/report/default-0/index.html"

            test_name_suffix=error
            grep -B 1 "/test/$test_name_suffix</td>" $HTML | tee $tmp/$test_name_suffix
            rlAssertGrep 'class="result error">error</td>' $tmp/$test_name_suffix -F

            test_name_suffix=fail
            grep -B 1 "/test/$test_name_suffix</td>" $HTML | tee $tmp/$test_name_suffix
            rlAssertGrep 'class="result fail">fail</td>' $tmp/$test_name_suffix -F

            test_name_suffix=pass
            grep -B 1 "/test/$test_name_suffix</td>" $HTML | tee $tmp/$test_name_suffix
            rlAssertGrep 'class="result pass">pass</td>' $tmp/$test_name_suffix -F

            test_name_suffix=timeout
            grep -B 1 "/test/$test_name_suffix</td>" $HTML | tee $tmp/$test_name_suffix
            rlAssertGrep 'class="result error">error</td>' $tmp/$test_name_suffix -F
            sed -e "/name\">\/test\/$test_name_suffix/,/\/tr/!d" $HTML | tee $tmp/$test_name_suffix-note
            rlAssertGrep '<td class="note">timeout</td>' $tmp/$test_name_suffix-note -F

            test_name_suffix=xfail
            grep -B 1 "/test/$test_name_suffix</td>" $HTML | tee $tmp/$test_name_suffix
            rlAssertGrep 'class="result pass">pass</td>' $tmp/$test_name_suffix -F
            sed -e "/name\">\/test\/$test_name_suffix/,/\/tr/!d" $HTML | tee $tmp/$test_name_suffix-note
            rlAssertGrep '<td class="note">original result: fail</td>' $tmp/$test_name_suffix-note -F

        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $tmp"
    rlPhaseEnd
rlJournalEnd
