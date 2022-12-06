#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1


function assert_execution_order(){
    local input_file="$tmp/run/plans${plan}/data/execution_order"
    sed -n 's;^.*execute/data\(.\+\)/data;\1;p' "$input_file" > $tmp/outcome
    rlRun "diff -pu $tmp/outcome $tmp/EXPECTED"
}

function assert_discover_order(){
    local input_file="$rlRun_LOG"
    # Discovered tests are printed with leading spaces
    sed -n 's;^ \+\(/.\+\);\1;p' "$input_file" > $tmp/outcome
    rlRun "diff -pu $tmp/outcome $tmp/EXPECTED"
}

function run_test(){
    rlPhaseStartTest "$plan"
        rlRun -s "tmt run --all --id $tmp/run --scratch plans -n $plan$ discover -vvv"
        rlLog "execution_order content:\n$(cat $tmp/run/plans${plan}/data/execution_order)"

        assert_discover_order
        assert_execution_order

        # Now in two parts
        rlRun -s "tmt run --id $tmp/run --scratch plans -n $plan$ discover -vvv"
        assert_discover_order

        rlRun -s "tmt run --all --id $tmp/run plans -n $plan$"
        assert_execution_order
    rlPhaseEnd
}


rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd order"
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
    rlPhaseEnd


    ### New test begins
    plan="/single-without-order-tag"
    cat > $tmp/EXPECTED <<EOF
/tests/no-order-0
/tests/no-order-1
/tests/no-order-2
EOF
    run_test

    ### New test begins
    plan="/single-without-order-name"
    cat > $tmp/EXPECTED <<EOF
/tests/no-order-0
/tests/no-order-1
/tests/no-order-2
EOF
    run_test

    ### New test begins
    plan="/single-enumerate"
    cat > $tmp/EXPECTED <<EOF
/tests/no-order-2
/tests/no-order-0
/tests/no-order-1
EOF
    run_test

    ### New test begins
    plan="/single-enumerate-and-order"
    cat > $tmp/EXPECTED <<EOF
/tests/no-order-2
/tests/order-80
/tests/no-order-0
/tests/no-order-1
EOF
    run_test

    ### New test begins
    plan="/single-order"
    cat > $tmp/EXPECTED <<EOF
/tests/order-10
/tests/no-order-0
/tests/no-order-1
/tests/no-order-2
/tests/order-80
EOF
    run_test

    ### New test begins
    plan="/multiple-by-enumerate"
    cat > $tmp/EXPECTED <<EOF
/enumerate-and-order/tests/no-order-2
/enumerate-and-order/tests/order-80
/enumerate-and-order/tests/no-order-0
/enumerate-and-order/tests/no-order-1
/by-order-attribute/tests/order-10
/by-order-attribute/tests/no-order-0
/by-order-attribute/tests/no-order-1
/by-order-attribute/tests/no-order-2
/by-order-attribute/tests/order-80
/third/order-20
/third/order-default
EOF
    run_test

    ### New test begins
    plan="/multiple-by-order"
    cat > $tmp/EXPECTED <<EOF
/order-10/tests/order-10
/order-10/tests/no-order-0
/order-10/tests/no-order-1
/order-10/tests/no-order-2
/order-10/tests/order-80
/order-default/order-20
/order-default/order-default
/order-80/tests/no-order-2
/order-80/tests/order-80
/order-80/tests/no-order-0
/order-80/tests/no-order-1
EOF
    run_test

    rlPhaseStartCleanup
        rlRun 'rm -rf $tmp' 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
