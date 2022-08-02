#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

set -o pipefail

rlJournalStart
    rlPhaseStartSetup "Prepare git repos"
        rlRun "repo1=\$(mktemp -d)"
        rlRun "mkdir $repo1/first"
        rlRun "cp data/lib.sh $repo1/first"
        rlRun "cp data/test.sh $repo1"
        cat <<EOF > $repo1/first/main.fmf
test: bash ../test.sh
framework: beakerlib
require:
- name: /second
  url: $repo1
EOF
        rlRun "tmt init $repo1"
        rlRun "cp -r $repo1/first $repo1/second"
        rlRun "sed s/first/second/g -i $repo1/second/lib.sh"
        rlRun "sed s/second/first/g -i $repo1/second/main.fmf"

        rlRun "pushd $repo1"
        rlRun "git init"
        rlRun "git config --local user.email me@localhost.localdomain"
        rlRun "git config --local user.name m e"
        rlRun "git add -A"
        rlRun "git commit -m initial"
    rlPhaseEnd

    rlPhaseStartTest "Libs in the same repo"
        rlRun -s "tmt run --rm -a -vvv -ddd provision -h local"
        rlAssertGrep "2 tests passed" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -rf $repo1" 0 "Remove temporary directories"
    rlPhaseEnd
rlJournalEnd
