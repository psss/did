#!/bin/bash

. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun 'set -o pipefail'
        rlRun "git clone https://src.fedoraproject.org/rpms/tmt.git $tmp/tmt"
        rlRun "cp data/plans.fmf $tmp/tmt/plans"
        rlRun 'pushd $tmp'
    rlPhaseEnd

    rlPhaseStartTest "Run directly from the DistGit (Fedora) [cli]"
        rlRun 'pushd tmt'
        rlRun -s 'tmt run --remove plans --default \
            discover -v --how fmf --dist-git-source \
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
            discover --how fmf --dist-git-source --dist-git-type Fedora --url $tmp/tmt \
            tests --name tests/prepare/install$'
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F
    rlPhaseEnd

    # FIXME - use globbing once it is possible (--path tmt-*/tests/execute/framework/data)
    for prefix in "" "/"; do
        rlPhaseStartTest "${prefix}path pointing to the fmf root in the extracted sources"
            rlRun 'pushd tmt'
            rlRun -s "tmt run --remove plans --default discover -v --how fmf \
            --dist-git-source --ref e2d36db --path ${prefix}tmt-1.7.0/tests/execute/framework/data \
            tests --name ^/tests/beakerlib/with-framework\$"
            rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F
            rlRun 'popd'
        rlPhaseEnd
    done

    rlPhaseStartTest "Specify URL and REF of DistGit repo (Fedora)"
        rlRun -s 'tmt run --remove plans --default discover -v --how fmf \
        --dist-git-source --ref e2d36db --url https://src.fedoraproject.org/rpms/tmt.git \
        tests --name tests/prepare/install$'
        rlAssertGrep "summary: 1 test selected" $rlRun_LOG -F
        rlAssertGrep "/tmt-1.7.0/tests/prepare/install" $rlRun_LOG -F
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
