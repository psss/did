#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlAssertRpm "httpd"
        rlRun "rlImport httpd/http"
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $tmp"
    rlPhaseEnd

    rlPhaseStartTest "Test http"
        rlRun "httpStart" 0 "Start http server"
        rlRun "httpStatus" 0 "Check server status"
        rlRun "httpStop" 0 "Stop http server"
    rlPhaseEnd

    rlPhaseStartTest "Test https"
        rlRun "httpsStart" 0 "Start https server"
        rlRun "httpInstallCa `hostname`" 0 "Install certificate"
        rlRun "httpsStatus" 0 "Check server status"
        rlRun "httpRemoveCa" 0 "Remove certificate"
        rlRun "httpsStop" 0 "Stop https server"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
