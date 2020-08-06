#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm "openssl"
        rlRun "rlImport openssl/certgen"
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "x509KeyGen ca"
        rlRun "x509KeyGen server"
        rlAssertExists "ca"
        rlAssertExists "server"
        # Also check for the 'tree' rpm if requested
        [[ "$1" == "tree" ]] && rlAssertRpm tree
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
