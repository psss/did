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

    rlPhaseStartTest "Recommend"
        rlRun "$tmt recommend | tee $tmp/output" 0
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

    rlPhaseStartTest "Missing"
        rlRun "$tmt missing/repository 2>&1 | tee $tmp/output" 2
        rlAssertGrep 'Authentication failed.*something' $tmp/output
        rlRun "$tmt missing/library 2>&1 | tee $tmp/output" 2
        rlAssertGrep 'dnf install.*openssl/wrong' $tmp/output
        rlRun "$tmt missing/metadata 2>&1 | tee $tmp/output" 2
        rlAssertGrep 'Repository .* does not contain fmf metadata.' $tmp/output
        rlRun "$tmt missing/reference 2>&1 | tee $tmp/output" 2
        rlAssertGrep 'Reference .* not found.' $tmp/output
    rlPhaseEnd

    rlPhaseStartTest "Deep"
        rlRun "$tmt file 2>&1 | tee $tmp/output"
        rlAssertGrep 'the library is stored deep.' $tmp/output
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
