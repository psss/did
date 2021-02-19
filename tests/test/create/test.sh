#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    DIR_DOT_SYNTAX="some/nice/dir/structure"
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
        rlRun "mkdir -p $DIR_DOT_SYNTAX"
        rlRun "set -o pipefail"
        rlRun "tmt init"
    rlPhaseEnd

    rlPhaseStartTest "Shell template"
        rlRun "tmt test create test_shell --template shell"
        rlAssertExists "$tmp/test_shell/main.fmf"
        rlAssertExists "$tmp/test_shell/test.sh"
    rlPhaseEnd

    rlPhaseStartTest "Existing directory and files"
        rlRun -s "tmt test create test_shell --template shell" \
            2 "test already exists"
        rlAssertGrep "File '$tmp/test_shell/main.fmf' already exists." \
            "${rlRun_LOG}"
        rlAssertGrep "Directory '$tmp/test_shell' already exists." \
            "${rlRun_LOG}"
        rlAssertExists "$tmp/test_shell/main.fmf"
        rlAssertExists "$tmp/test_shell/test.sh"
    rlPhaseEnd

    rlPhaseStartTest "BeakerLib template"
        rlRun "tmt test create test_beakerlib --template beakerlib"
        rlAssertExists "$tmp/test_beakerlib/main.fmf"
        rlAssertExists "$tmp/test_beakerlib/test.sh"
    rlPhaseEnd

    rlPhaseStartTest "non-existent template"
        rlRun -s "tmt test create non-existent --template non-existent" \
            2 "Template doesn't exist"
        rlAssertGrep "Invalid template 'non-existent'." "${rlRun_LOG}"
    rlPhaseEnd

    rlPhaseStartTest "Using the '.' syntax"
        rlRun "cd $DIR_DOT_SYNTAX"
        rlRun "tmt test create . --template shell"
        rlAssertExists "$tmp/$DIR_DOT_SYNTAX/main.fmf"
        rlAssertExists "$tmp/$DIR_DOT_SYNTAX/test.sh"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
