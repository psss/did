#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        export REPO="$(pwd)/../.."
        export REV="$(git rev-parse --short HEAD)"
        rlRun "set -o pipefail"
    rlPhaseEnd

for WHAT in "tests-" "plans-" "stories-" ''; do
    hook="tmt-${WHAT}lint"

    rlPhaseStartTest "Hook: $hook"
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"

        rlRun "tmt init"
        rlRun "git init"
        rlRun "git config --local user.name LZachar"
        rlRun "git config --local user.email lzachar@redhat.com"
cat <<EOF > .pre-commit-config.yaml
repos:
  - repo: $REPO
    rev: "$REV"
    hooks:
    - id: "$hook"
EOF
        if [ -n "$WHAT" ]; then
            expected_command="tmt ${WHAT%-} lint"
        else
            expected_command="tmt lint"
        fi
        rlRun "cat .pre-commit-config.yaml"
        rlRun -s "pre-commit install"
        rlAssertGrep 'pre-commit installed' $rlRun_LOG
        rlRun -s "git add .pre-commit-config.yaml"
        rlRun -s "git commit -m nothing_to_check"
        # No *fmf file modified
        rlAssertGrep "$expected_command.*no files to check" $rlRun_LOG

        case $WHAT in
            tests-|"")
                rlRun "echo 'test: echo' > main.fmf"
                ;;
            stories-)
                rlRun "echo 'story: whatever' > main.fmf"
                ;;
            plans-)
                rlRun "echo -e 'execute:\n  how: tmt' > main.fmf"
                ;;
        esac

        rlRun "git add main.fmf"
        rlRun -s "git commit -m 'missing_fmf_root'" "1"
        # .fmf/version was not added
        rlAssertGrep "$expected_command.*Failed" $rlRun_LOG

        rlRun "git add .fmf/version"
        rlRun -s "git commit -m 'pass'"
        # All good
        rlAssertGrep "$expected_command.*Passed" $rlRun_LOG

        rlRun "echo foo: bar > wrong.fmf"
        rlRun "git add wrong.fmf"
        rlRun -s "git commit -m wrong" "1"
        # Test uses invalid attribute
        rlAssertGrep "$expected_command.*Failed" $rlRun_LOG
        rlAssertGrep 'fail unknown attribute' $rlRun_LOG

        # Force broken test into repo
        rlRun -s "git commit --no-verify -m wrong" "0"

        # Add another good test, pre-commit should pass because /wrong
        # is not touched
        rlRun "echo summary: hello world > good.fmf"
        rlRun "git add good.fmf"
        rlRun -s "git commit -m 'add_good'"
        rlAssertGrep "$expected_command.*Passed" $rlRun_LOG

        # Modify main.fmf so both /good and /wrong are checked
        rlRun "echo summary: foo >> main.fmf"
        rlRun -s "git commit -a -m 'modify_main'" "1"
        rlAssertGrep "$expected_command.*Failed" $rlRun_LOG
        rlAssertGrep '/good' $rlRun_LOG
        rlAssertGrep '/wrong' $rlRun_LOG

        rlRun "popd"
        rlRun "rm -rf $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
done
rlJournalEnd
