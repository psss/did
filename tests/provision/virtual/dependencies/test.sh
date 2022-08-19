#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

USER="tester"

rlJournalStart
    rlPhaseStartSetup
        # Directories
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "run=\$(mktemp -d)" 0 "Create run directory"
        rlRun "pushd $tmp"
        # Test user
        rlRun "useradd $USER" 0 "Create test user"
        rlRun "loginctl enable-linger $USER" 0 "Enable /run/user directory"
        rlRun "chown $USER $tmp $run" 0 "Set permissions"
    rlPhaseEnd

    rlPhaseStartTest "Test session connection"
        command="tmt run --id $run --verbose --scratch \
            provision --how virtual --memory 1500 --connection session \
            login -c \"echo works fine\" \
            finish"
        rlRun "su -l $USER -c '$command'"
    rlPhaseEnd

    rlPhaseStartTest "Test system connection"
        rlRun "systemctl start libvirtd"
        rlRun "usermod --append --groups libvirt $USER"
        command="tmt run --id $run --verbose --scratch \
            provision --how virtual --memory 1500 --connection system \
            login -c \"echo works fine\" \
            finish"
        rlRun "su -l $USER -c '$command'"
        rlRun "systemctl stop libvirtd"
    rlPhaseEnd

    rlPhaseStartCleanup
        # Test user
        rlRun "loginctl terminate-user $USER" 0,1 "Terminate session"
        rlRun "pkill -u $USER" 0,1 "Kill user processes"
        rlRun "userdel -r $USER" 0 "Remove the test user"
        # Directories
        rlRun "popd"
        rlRun "rm -r $tmp $run" 0 "Remove tmp and run directory"
    rlPhaseEnd
rlJournalEnd
