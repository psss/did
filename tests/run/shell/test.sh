#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

USER=test_user$$

rlJournalStart
    rlPhaseStartSetup

        [[ $(id -u) -eq 0 ]] || rlDie "Test has to run as root"

        rlRun "set -o pipefail"
        rlRun "useradd -s $(which zsh) $USER"

        # Copy data and change ownership
        rlRun "cp -rv data /home/$USER"
        rlRun "chown $USER:$USER -R /home/$USER"

        rlRun "rlFileBackup \"/bin/sh\""
        # Defaults to /bin/sh so we need to change that to not bash
        rlRun "ln -sf $(which zsh) /bin/sh"
    rlPhaseEnd

    rlPhaseStartTest
        # BASH_VERSION is not set unless in running in BASH
        # Reproducer plan uses 'local' provisioner.
        # as of now support for 'user' in virtual is not always working
        rlRun "su -l -c 'cd data && tmt run -v --id /home/$USER/run_id plan --name /reproducer' $USER"
        rlBundleLogs "log_txt" "/home/$USER/run_id/log.txt"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rlFileRestore"
        rlRun "loginctl terminate-user $USER" 0,1
        rlRun "pkill -u $USER" 0,1
        rlRun "userdel -r $USER"
    rlPhaseEnd
rlJournalEnd
