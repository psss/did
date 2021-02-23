#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "tmt test show"
        rlRun 'tmt test show | tee output'
        rlAssertGrep 'verifies /stories/covered' output
        rlAssertGrep 'verifies /stories/verified' output
        rlAssertGrep 'relates https://github.com' output
    rlPhaseEnd

    rlPhaseStartTest "tmt plan show"
        rlRun 'tmt plan show | tee output'
        rlAssertGrep 'verifies /stories/covered' output
        rlAssertGrep 'verifies /stories/verified' output
        rlAssertGrep 'blocks /plans/full' output
        rlAssertGrep 'relates https://github.com' output
    rlPhaseEnd

    rlPhaseStartTest "tmt story show"
        rlRun 'tmt story show covered | tee output'
        rlAssertGrep 'verified /test/example' output
        rlAssertGrep 'documented /docs/example' output
        rlAssertGrep 'implemented /code/example' output
        rlRun 'tmt story show idea | tee output'
        rlAssertNotGrep 'verified /test/example' output
        rlAssertNotGrep 'documented /docs/example' output
        rlAssertNotGrep 'implemented /code/example' output
    rlPhaseEnd

    rlPhaseStartTest "tmt story coverage"
        rlRun 'tmt story coverage | tee output'
        rlAssertGrep 'done done done /stories/covered' output
        rlAssertGrep 'todo todo todo /stories/idea' output
        rlRun 'tmt story coverage --implemented | tee output'
        rlAssertGrep '/stories/covered' output
        rlAssertGrep '/stories/implemented' output
        rlAssertNotGrep '/stories/verified' output
        rlAssertNotGrep '/stories/documented' output
        rlRun 'tmt story coverage --unimplemented | tee output'
        rlAssertNotGrep '/stories/covered' output
        rlAssertNotGrep '/stories/implemented' output
        rlAssertGrep '/stories/verified' output
        rlAssertGrep '/stories/documented' output
        rlRun 'tmt story coverage non-existent | tee output'
        rlRun 'wc -l output | grep 0'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -f output"
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
