#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1


SERVER_PORT="9000"
MOCK_SOURCES_FILENAME='mock_sources'

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'set -o pipefail'
        rlRun "git clone https://src.fedoraproject.org/rpms/tmt.git $tmp/tmt"
        export CLONED_TMT=$tmp/tmt
        rlRun "cp data/plans.fmf $CLONED_TMT/plans"
        # Append existing TMT_PLUGINS content
        rlRun "export TMT_PLUGINS=$(pwd)/data${TMT_PLUGINS:+:$TMT_PLUGINS}"
        rlRun 'pushd $tmp'

        # server runs in $tmp
        rlRun "python3 -m http.server $SERVER_PORT &> server.out &"
        SERVER_PID="$!"
        rlRun "rlWaitForSocket $SERVER_PORT -t 5 -d 1"
        export SERVER_DIR="$(pwd)"

        # prepare cwd for mock distgit tests
        rlRun "mkdir $tmp/mock_distgit"
        export MOCK_DISTGIT_DIR=$tmp/mock_distgit
        rlRun "pushd $MOCK_DISTGIT_DIR"
        rlRun "git init" # should be git
        rlRun "tmt init" # should has fmf tree

        # Contains one test
        echo 'test: echo' > top_test.fmf

        # prepare simple-1
        (
            rlRun "mkdir -p $tmp/simple-1/tests"
            (
                rlRun "cd $tmp/simple-1"
                rlRun "tmt init"
            )
            echo 'test: echo' > "$tmp/simple-1/tests/magic.fmf"
            touch $tmp/outsider
            rlRun "tar czvf $tmp/simple-1.tgz --directory $tmp simple-1 outsider"
            rlRun "rm -rf $tmp/simple-1 outsider"
        )

        # prepare unit-no-tmt (e.g. pytest files inside tarball)
        (
            rlRun "mkdir -p $tmp/foo-123"
            echo -e '#!/bin/sh\necho WORKS'> $tmp/foo-123/all_in_one
            chmod a+x $tmp/foo-123/all_in_one

            rlRun "tar czvf $tmp/unit-no-tmt.tgz --directory $tmp foo-123"
            rlRun "rm -rf $tmp/foo-123"
        )

        rlRun "popd"
    rlPhaseEnd


    ### discover -h fmf ###

for value in explicit auto; do
    rlPhaseStartTest "extract sources to find unit tests (merge $value)"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'pushd $tmp'

        rlRun "git init && tmt init" # should be git with fmf tree

        # own "sources" for testing
        echo "unit-no-tmt.tgz" > $MOCK_SOURCES_FILENAME

# This can't be supported (mixing tests defined in discover and execute)
#         cat <<EOF > plans.fmf
# discover:
#     how: fmf
#     dist-git-source: true
#     dist-git-type: TESTING
# provision:
#     how: local
# execute:
#     how: tmt
#     script: foo-123/all_in_one
# EOF

        cat <<EOF > plans.fmf
discover:
    how: fmf
    dist-git-source: true
    dist-git-type: TESTING
    dist-git-merge: true
provision:
    how: local
execute:
    how: tmt
EOF

    if [[ "$value" == "auto" ]]; then
        rlRun "sed '/dist-git-merge:/d' -i plans.fmf"
    fi
        echo 'test: foo-123/all_in_one' > unit.fmf

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_TESTS=$WORKDIR/plans/discover/default/tests

        rlRun -s "tmt run -vv --id $WORKDIR --scratch"

        rlAssertGrep "/unit" $rlRun_LOG -F
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F

        rlAssertExists $WORKDIR_TESTS/foo-123/all_in_one

        rlRun "popd"
        rlRun "rm $rlRun_LOG"
        rlRun "rm -rf $tmp"
    rlPhaseEnd
done

    rlPhaseStartTest "More source files (fmf root in one of them)"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'pushd $tmp'

        rlRun "git init" # should be git
        rlRun "tmt init" # should has fmf tree

        (
            echo simple-1.tgz
            echo unit-no-tmt.tgz
        ) > $MOCK_SOURCES_FILENAME

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_SOURCE=$WORKDIR/plans/default/discover/default/source
        WORKDIR_TESTS=$WORKDIR/plans/default/discover/default/tests

        rlRun -s "tmt run --id $WORKDIR --scratch plans --default \
             discover -vvv -ddd --how fmf --dist-git-source \
             --dist-git-type TESTING tests --name /tests/magic"
        rlAssertGrep "\s/tests/magic" $rlRun_LOG -E
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F

        # Source dir has everything available
        rlAssertExists $WORKDIR_SOURCE/simple-1/tests/magic.fmf
        rlAssertExists $WORKDIR_SOURCE/simple-1.tgz
        rlAssertExists $WORKDIR_SOURCE/foo-123/all_in_one
        rlAssertExists $WORKDIR_SOURCE/unit-no-tmt.tgz
        rlAssertExists $WORKDIR_SOURCE/outsider

        # Test dir has only fmf_root from source (so one less level)
        rlAssertExists $WORKDIR_TESTS/tests/magic.fmf
        rlAssertNotExists $WORKDIR_TESTS/simple-1/tests/magic.fmf
        rlAssertNotExists $WORKDIR_TESTS/simple-1.tgz
        rlAssertNotExists $WORKDIR_TESTS/foo-123/all_in_one
        rlAssertNotExists $WORKDIR_TESTS/unit-no-tmt.tgz
        rlAssertNotExists $WORKDIR_TESTS/outsider

        rlRun "popd"
        rlRun "rm $rlRun_LOG"
        rlRun "rm -rf $tmp"
    rlPhaseEnd



    rlPhaseStartTest "signature files in sources are ignored"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'pushd $tmp'

        rlRun "git init" # should be git
        rlRun "tmt init" # should has fmf tree

        # https://github.com/teemtee/tmt/issues/1055

        (
            echo simple-1.tgz
            echo IGNORED file.tgz.asc
            echo IGNORED file.key
            echo IGNORED file.sign
        ) > $MOCK_SOURCES_FILENAME
        # only simple-1.tgz should be downloaded so all other would fail with
        # File not found for url: http://localhost:9000/IGNORED

        rlRun -s 'tmt run --id /var/tmp/tmt/XXX --scratch plans --default \
             discover -vvv -ddd --how fmf --dist-git-source \
             --dist-git-type TESTING tests --name /magic'
        rlAssertGrep "/magic" $rlRun_LOG -F
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F

        rlRun "popd"
        rlRun "rm $rlRun_LOG"
        rlRun "rm -rf $tmp"
    rlPhaseEnd

    rlPhaseStartTest "Detect within extracted sources (inner fmf root is used)"
        rlRun 'pushd $MOCK_DISTGIT_DIR'

        echo "simple-1.tgz" > $MOCK_SOURCES_FILENAME

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_SOURCE=$WORKDIR/plans/default/discover/default/source
        WORKDIR_TESTS=$WORKDIR/plans/default/discover/default/tests

        rlRun -s 'tmt run --id $WORKDIR --scratch plans --default \
             discover -vvv -ddd --how fmf --dist-git-source \
             --dist-git-type TESTING'
        rlAssertNotGrep "/top_test" $rlRun_LOG -F
        rlAssertGrep "/magic" $rlRun_LOG -F
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F

        # Source dir has everything available
        rlAssertExists $WORKDIR_SOURCE/outsider
        rlAssertExists $WORKDIR_SOURCE/simple-1
        rlAssertExists $WORKDIR_SOURCE/simple-1.tgz

        # Test dir has only fmf_root from source
        rlAssertExists $WORKDIR_TESTS/tests/magic.fmf
        rlAssertNotExists $WORKDIR_TESTS/outsider
        rlAssertNotExists $WORKDIR_TESTS/simple-1
        rlAssertNotExists $WORKDIR_TESTS/simple-1.tgz

        rlRun 'popd'
    rlPhaseEnd

    rlPhaseStartTest "Detect within extracted sources and join with plan data (still respect fmf root)"
        rlRun 'pushd $MOCK_DISTGIT_DIR'

        echo "simple-1.tgz" > $MOCK_SOURCES_FILENAME

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_SOURCE=$WORKDIR/plans/default/discover/default/source
        WORKDIR_TESTS=$WORKDIR/plans/default/discover/default/tests

        rlRun -s 'tmt run --id $WORKDIR --scratch plans --default \
            discover -v --how fmf --dist-git-source \
            --dist-git-type TESTING --dist-git-merge'
        rlAssertGrep "\s/top_test" $rlRun_LOG -E
        rlAssertGrep "\s/tests/magic" $rlRun_LOG -E
        rlAssertGrep "summary: 2 tests selected" $rlRun_LOG -F

        # Source dir has everything available
        rlAssertExists $WORKDIR_SOURCE/outsider
        rlAssertExists $WORKDIR_SOURCE/simple-1
        rlAssertExists $WORKDIR_SOURCE/simple-1.tgz

        # Only fmf_root from source was merged
        rlAssertExists $WORKDIR_TESTS/tests/magic.fmf
        rlAssertNotExists $WORKDIR_TESTS/outsider
        rlAssertNotExists $WORKDIR_TESTS/simple-1
        rlAssertNotExists $WORKDIR_TESTS/simple-1.tgz
        rlRun 'popd'
    rlPhaseEnd

    rlPhaseStartTest "Detect within extracted sources and join with plan data (override fmf root)"
        rlRun 'pushd $MOCK_DISTGIT_DIR'

        echo "simple-1.tgz renamed_simple.tgz" > $MOCK_SOURCES_FILENAME

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_SOURCE=$WORKDIR/plans/default/discover/default/source
        WORKDIR_TESTS=$WORKDIR/plans/default/discover/default/tests

        rlRun -s 'tmt run --id $WORKDIR --scratch plans --default \
            discover -v --how fmf --dist-git-source \
            --dist-git-type TESTING --dist-git-merge --dist-git-extract /simple*/tests'
        rlAssertGrep "\s/top_test" $rlRun_LOG -E
        rlAssertGrep "\s/magic" $rlRun_LOG -E
        rlAssertGrep "summary: 2 tests selected" $rlRun_LOG -F

        # Source dir has everything available
        rlAssertExists $WORKDIR_SOURCE/outsider
        rlAssertExists $WORKDIR_SOURCE/simple-1
        rlAssertExists $WORKDIR_SOURCE/renamed_simple.tgz

        # copy path set to /tests within sources, so simple-1 is not copied
        rlAssertExists $WORKDIR_TESTS/magic.fmf
        rlAssertNotExists $WORKDIR_TESTS/outsider
        rlAssertNotExists $WORKDIR_TESTS/simple-1
        rlAssertNotExists $WORKDIR_TESTS/renamed_simple.tgz
        rlRun 'popd'
    rlPhaseEnd

    rlPhaseStartTest "Detect within extracted sources and join with plan data (strip fmf root)"
        rlRun 'pushd $MOCK_DISTGIT_DIR'

        echo "simple-1.tgz simple.tgz" > $MOCK_SOURCES_FILENAME

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_SOURCE=$WORKDIR/plans/default/discover/default/source
        WORKDIR_TESTS=$WORKDIR/plans/default/discover/default/tests

        rlRun -s 'tmt run --id $WORKDIR --scratch plans --default \
            discover -v --how fmf --dist-git-source \
            --dist-git-type TESTING --dist-git-merge --dist-git-remove-fmf-root'
        rlAssertGrep "\s/top_test" $rlRun_LOG -E
        rlAssertGrep "\s/simple-1/tests/magic" $rlRun_LOG -E
        rlAssertGrep "summary: 2 tests selected" $rlRun_LOG -F

        # Source dir has everything available
        rlAssertExists $WORKDIR_SOURCE/outsider
        rlAssertExists $WORKDIR_SOURCE/simple-1
        rlAssertExists $WORKDIR_SOURCE/simple.tgz

        # fmf root stripped and dist-git-extract not set so everything is copied
        rlAssertExists $WORKDIR_TESTS/simple-1/tests/magic.fmf
        rlAssertExists $WORKDIR_TESTS/outsider
        rlAssertExists $WORKDIR_TESTS/simple-1
        rlAssertExists $WORKDIR_TESTS/simple.tgz
        rlRun 'popd'
    rlPhaseEnd

    rlPhaseStartTest "Run directly from the DistGit (Fedora) [cli]"
        rlRun 'pushd tmt'
        rlRun -s 'tmt run --remove plans --default \
            discover -v --how fmf --dist-git-source --dist-git-init \
            tests --name tests/prepare/install$'
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F
        rlAssertGrep "/tests/prepare/install" $rlRun_LOG -F
        rlRun 'popd'
    rlPhaseEnd

    rlPhaseStartTest "Run directly from the DistGit (Fedora) [plan]"
        rlRun 'pushd tmt'
        rlRun -s 'tmt run --remove plans --name distgit discover -v'
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F
        rlAssertGrep "/tests/prepare/install" $rlRun_LOG -F
        rlRun 'popd'
    rlPhaseEnd

    rlPhaseStartTest "URL is path to a local distgit repo"
        rlRun -s 'tmt run --remove plans --default \
            discover --how fmf --dist-git-source --dist-git-type fedora --url $CLONED_TMT \
            --dist-git-init --dist-git-merge tests --name tests/prepare/install$'
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F
    rlPhaseEnd

    for prefix in "" "/"; do
        rlPhaseStartTest "${prefix}path pointing to the fmf root in the extracted sources"
            rlRun 'pushd tmt'
            rlRun -s "tmt run --remove plans --default discover -v --how fmf \
            --dist-git-source --dist-git-merge --ref e2d36db --dist-git-extract ${prefix}tmt-*/tests/execute/framework/data \
            tests --name ^/tests/beakerlib/with-framework\$"
            rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F

            rlRun 'popd'
        rlPhaseEnd
    done

    rlPhaseStartTest "Specify URL and REF of DistGit repo (Fedora)"
        rlRun -s 'tmt run --remove plans --default discover -v --how fmf \
        --dist-git-source --ref e2d36db --dist-git-merge  --dist-git-init \
        --url https://src.fedoraproject.org/rpms/tmt.git \
        tests --name tests/prepare/install$'
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F
        rlAssertGrep "/tmt-1.7.0/tests/prepare/install" $rlRun_LOG -F
    rlPhaseEnd

    rlPhaseStartTest "fmf and git root don't match"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'pushd $tmp'

        rlRun "git init" # should be git

        (
            echo simple-1.tgz
            echo unit-no-tmt.tgz
        ) > $MOCK_SOURCES_FILENAME

        rlRun "mkdir fmf"
        rlRun "pushd fmf"
        rlRun "tmt init"

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_SOURCE=$WORKDIR/plans/default/discover/default/source
        WORKDIR_TESTS=$WORKDIR/plans/default/discover/default/tests

        rlRun -s "tmt run --id $WORKDIR --scratch plans --default \
             discover -vvv -ddd --how fmf --dist-git-source \
             --dist-git-type TESTING tests --name /tests/magic"
        rlAssertGrep "\s/tests/magic" $rlRun_LOG -E
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F

        # Source dir has everything available
        rlAssertExists $WORKDIR_SOURCE/simple-1/tests/magic.fmf
        rlAssertExists $WORKDIR_SOURCE/simple-1.tgz
        rlAssertExists $WORKDIR_SOURCE/foo-123/all_in_one
        rlAssertExists $WORKDIR_SOURCE/unit-no-tmt.tgz
        rlAssertExists $WORKDIR_SOURCE/outsider

        # Test dir has only fmf_root from source (so one less level)
        rlAssertExists $WORKDIR_TESTS/tests/magic.fmf
        rlAssertNotExists $WORKDIR_TESTS/simple-1/tests/magic.fmf
        rlAssertNotExists $WORKDIR_TESTS/simple-1.tgz
        rlAssertNotExists $WORKDIR_TESTS/foo-123/all_in_one
        rlAssertNotExists $WORKDIR_TESTS/unit-no-tmt.tgz
        rlAssertNotExists $WORKDIR_TESTS/outsider

        rlRun "popd"
        rlRun "popd"
        rlRun "rm $rlRun_LOG"
        rlRun "rm -rf $tmp"
    rlPhaseEnd

    ### discover -h shell ###

    rlPhaseStartTest "shell with merge (tmt for plan only)"
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'pushd $tmp'

        rlRun "git init"
        echo unit-no-tmt.tgz > $MOCK_SOURCES_FILENAME

        rlRun "tmt init"
        cat <<EOF > plans.fmf
discover:
    how: shell
    tests:
    -   name: /file-exists
        test: ls \$TMT_SOURCE_DIR/foo-123/all_in_one
        environment:
            FOO: bar
    -   name: /env-is-kept
        test: declare -p FOO && test \$FOO == bar
        environment:
            FOO: bar
    -   name: /run-it
        test: cd \$TMT_SOURCE_DIR/foo* && sh all_in_one
    dist-git-source: true
    dist-git-type: TESTING
provision:
    how: local
execute:
    how: tmt
EOF

        WORKDIR=/var/tmp/tmt/XXX
        WORKDIR_SOURCE=$WORKDIR/plans/discover/default/source

        rlRun -s "tmt run --id $WORKDIR --scratch -vvv"

        # Source dir has everything available
        rlAssertExists $WORKDIR_SOURCE/foo-123/all_in_one
        rlAssertExists $WORKDIR_SOURCE/unit-no-tmt.tgz

        rlRun "popd"
        rlRun "rm $rlRun_LOG"
        rlRun "rm -rf $tmp"
    rlPhaseEnd


    rlPhaseStartCleanup
        echo $SERVER_PID
        kill -9 $SERVER_PID
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
