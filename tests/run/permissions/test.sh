#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

USER="tester-$$"

function user_cleanup {
    local user="$1"
    rlRun "pkill -u $user" 0,1
    # user session might be doing scripts
    command -v loginctl >/dev/null && rlRun "loginctl terminate-user $user" 0,1
    rlRun "userdel -r $user"
}

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
        rlRun "tmt init"
        cat <<EOF > plan.fmf
provision:
    how: local
execute:
    how: tmt
    script: echo
EOF
        rlRun "chmod 777 -R $tmp"
        rlRun "set -o pipefail"

        rlRun "useradd $USER"


        rlRun "export WORKDIR_ROOT=\"\$(python3 -c 'import tmt; print(tmt.utils.WORKDIR_ROOT)')\""
        rlLog "WORKDIR_ROOT=$WORKDIR_ROOT"
    rlPhaseEnd

    rlPhaseStartTest "Correct rpm ownership and permissions"
        rlAssertEquals "Owned by python3-tmt" "$(rpm -qf $WORKDIR_ROOT --qf '%{name}')" "python3-tmt"
        rlAssertEquals "Correct permission" "$(stat --format '%a' $WORKDIR_ROOT)" "1777"
    rlPhaseEnd

    rlPhaseStartTest "Recreated correctly"
        rlFileBackup --clean "$WORKDIR_ROOT"
        rlRun "rm -rf $WORKDIR_ROOT"
        rlRun "tmt run"
        rlAssertEquals "Correct permission" "$(stat --format '%a' $WORKDIR_ROOT)" "1777"
        # Another user can use WORKDIR_ROOT
        rlRun "su -l -c 'cd $tmp; tmt run' '$USER'"
        rlFileRestore
    rlPhaseEnd


    rlPhaseStartCleanup
        rlRun "popd"
        user_cleanup "$USER"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
