#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "cp -a data $tmp"
        rlRun 'pushd $tmp/data/parent/child'
        rlRun 'set -o pipefail'
    rlPhaseEnd

    rlPhaseStartTest 'Import metadata'
        rlRun 'tmt test import --no-nitrate | tee output'
        rlAssertGrep 'Makefile found in' 'output'
        rlAssertGrep 'summary: Simple smoke test' 'main.fmf'
        rlRun 'grep -A1 require main.fmf | grep tmt'
        rlRun 'grep -A1 recommend main.fmf | grep fmf'
    rlPhaseEnd

    rlPhaseStartTest 'Check duplicates'
        rlAssertNotGrep 'component:' 'main.fmf'
        rlAssertNotGrep 'test:' 'main.fmf'
        rlAssertNotGrep 'duration:' 'main.fmf'
    rlPhaseEnd

    rlPhaseStartTest 'Check rhts-environment removal'
        rlAssertGrep 'Removing.*rhts-environment' 'output'
        rlAssertNotGrep 'rhts-environment' 'runtest.sh'
    rlPhaseEnd

    rlPhaseStartTest 'Check beakerlib path update'
        rlAssertGrep 'Replacing old beakerlib path' 'output'
        rlAssertGrep '/usr/share/beakerlib/beakerlib.sh' 'runtest.sh'
        rlAssertNotGrep '/usr/lib/beakerlib/beakerlib.sh' 'runtest.sh'
        rlAssertNotGrep '/usr/share/rhts-library/rhtslib.sh' 'runtest.sh'
    rlPhaseEnd

    rlPhaseStartTest 'Import Restraint metadata'
        rlRun 'tmt test import --restraint --no-nitrate | tee output'
        rlAssertGrep 'Restraint file found in' 'output'
        rlAssertGrep 'summary: Simple smoke test using restraint' 'main.fmf'
	rlRun 'grep -A2 require main.fmf | grep "fmf\|tmt"'
        rlRun 'grep -A1 recommend main.fmf | grep fmf'
        rlAssertGrep 'test: ./runtest.sh' 'output'
        rlAssertGrep 'duration: 6m' 'main.fmf'
    rlPhaseEnd

    rlPhaseStartTest 'Import both Makefile and Restraint metadata. Expect Restraint to be used.'
        rlRun 'tmt test import --makefile --restraint --no-nitrate | tee output'
        rlAssertGrep 'Restraint file found in' 'output'
        rlAssertGrep 'summary: Simple smoke test using restraint' 'main.fmf'
	rlRun 'grep -A2 require main.fmf | grep "fmf\|tmt"'
        rlRun 'grep -A1 recommend main.fmf | grep fmf'
        rlAssertGrep 'test: ./runtest.sh' 'output'
        rlAssertGrep 'duration: 6m' 'main.fmf'
    rlPhaseEnd

    rlPhaseStartTest 'Import specifying not to use Makefile. Verify an error is returned.'
        rlRun 'tmt test import --no-makefile --no-nitrate 2>&1 | tee output' 2
        rlAssertGrep 'Please specify either a Makefile or Restraint file.' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Import specifying not to use Makefile or Restraint. Verify an error is returned.'
        rlRun 'tmt test import --no-makefile --no-restraint --no-nitrate 2>&1 | tee output' 2
        rlAssertGrep 'Please specify either a Makefile or Restraint file.' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Import metadata'
        rlRun 'tmt test import --no-nitrate | tee output'
        rlAssertGrep 'Makefile found in' 'output'
        rlAssertGrep 'summary: Simple smoke test' 'main.fmf'
        rlAssertGrep 'duration: 5m' 'output'
        rlRun 'grep -A1 require main.fmf | grep tmt'
        rlRun 'grep -A1 recommend main.fmf | grep fmf'
    rlPhaseEnd

    rlPhaseStartTest 'Verify error returned when no Makefile exists.'
        rlFileBackup "$tmp/data/parent/child/Makefile"
        rlRun "rm -f $tmp/data/parent/child/Makefile" 0 "Removing Makefile"
        rlRun 'tmt test import --no-nitrate 2>&1 | tee output' 2
        rlAssertGrep 'Unable to find Makefile' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Verify error returned when no Restraint metadata file exists.'
        rlFileBackup "$tmp/data/parent/child/metadata"
        rlRun "rm -f $tmp/data/parent/child/metadata" 0 "Removing Restraint file."
        rlRun 'tmt test import --restraint --no-nitrate 2>&1 | tee output' 2
        rlAssertGrep 'Unable to find any metadata file.' 'output'
        rlFileRestore
    rlPhaseEnd

    rlPhaseStartTest 'Verify inheritance'
        rlRun 'tmt test show | tee output'
        rlAssertGrep 'component tmt' 'output'
        rlAssertGrep 'test ./runtest.sh' 'output'
        rlAssertGrep 'duration 5m' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Check Makefile environment variables'
        rlRun 'tmt test show | tee output'
        rlAssertGrep 'AVC_ERROR: +no_avc_check' 'output'
        rlAssertGrep 'TEST: one two three' 'output'
        rlAssertGrep 'CONTEXT: distro=fedora' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Relevant bugs'
        rlRun 'tmt test show | tee output'
        rlAssertGrep 'relates.*1234567' 'output'
        rlAssertGrep 'relates.*2222222' 'output'
        rlAssertGrep 'relates.*9876543' 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Multihost'
        rlRun "tmt tests ls . --filter 'tag:multihost' | tee output"
        rlAssertGrep "/parent/child" 'output'
    rlPhaseEnd

    rlPhaseStartTest 'Type'
        import="tmt test import --no-nitrate"
        rlRun "$import --type all | tee output"
        rlAssertGrep "tag: Multihost Sanity KernelTier1" 'output'
        rlRun 'tmt test show | tee output'
        rlAssertGrep "tag Multihost, Sanity and KernelTier1" 'output'
        rlRun "$import --type KernelTier1 | tee output"
        rlAssertGrep 'tag: KernelTier1$' 'output'
        rlRun 'tmt test show | tee output'
        rlAssertGrep "tag KernelTier1$" 'output'
        rlRun "$import --type KernelTier1 --type SaNiTy | tee output"
        rlAssertGrep "tag: KernelTier1 SaNiTy" 'output'
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
        rlRun 'popd'
    rlPhaseEnd
rlJournalEnd
