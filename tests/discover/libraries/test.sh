#!/bin/bash
# vim: dict+=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "tmt='tmt run -avvvddd plan --name'"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    rlPhaseStartTest "Certificate"
        rlRun "$tmt 'rpm|fmf|nick|duplicate' | tee $tmp/output"
        rlAssertGrep "Fetch library 'openssl/certgen'" $tmp/output
    rlPhaseEnd

    rlPhaseStartTest "Apache"
        rlRun "$tmt apache | tee $tmp/output"
        rlAssertGrep "Fetch library 'httpd/http'" $tmp/output
        rlAssertGrep "Fetch library 'openssl/certgen'" $tmp/output
    rlPhaseEnd

    rlPhaseStartTest "Conflict"
        rlRun "$tmt conflict 2>&1 | tee $tmp/output" 2
        rlAssertGrep 'Library.*conflicts' $tmp/output
    rlPhaseEnd

    rlPhaseStartTest "Destination"
        rlRun "$tmt destination 2>&1 | tee $tmp/output" 1
        rlAssertGrep 'Cloning into.*custom/openssl' $tmp/output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
