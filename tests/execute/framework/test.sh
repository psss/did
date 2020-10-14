#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd data"
        rlRun "set -o pipefail"
    rlPhaseEnd

    # Old tests without framework
    sh1="/tests/shell/without-framework"
    bl1="/tests/beakerlib/without-framework"

    # New tests with framework
    sh2="/tests/shell/with-framework"
    bl2="/tests/beakerlib/with-framework"

    # Common tmt command line
    tmt="tmt run -avvvdddr"

    # Old execute methods
    for execute in tmt detach; do
        for framework in shell beakerlib; do
            rlPhaseStartTest "Old execute methods ($framework.$execute)"
                rlRun "$tmt execute -h $framework.$execute \
                        2>&1 | tee output" 0,2
                rlAssertGrep 'execute method has been deprecated' output
                # Default framework should be picked from the old method
                rlAssertGrep "Execute '$sh1' as a '$framework' test." output
                rlAssertGrep "Execute '$bl1' as a '$framework' test." output
                # Explicit framework in test should always override default
                rlAssertGrep "Execute '$sh2' as a 'shell' test." output
                rlAssertGrep "Execute '$bl2' as a 'beakerlib' test." output
                # Beakerlib tests should always install beakerlib
                if [[ $framework == beakerlib ]]; then
                    rlAssertGrep "dnf install.*beakerlib" output
                fi
                rlAssertGrep "warn.*execute.*deprecated" output
            rlPhaseEnd
        done
    done

    # New execute methods
    for execute in tmt detach; do
        rlPhaseStartTest "Combine shell and beakerlib ($execute)"
            rlRun "$tmt execute --how $execute 2>&1 | tee output"
            # The default test framework should be 'shell'
            rlAssertGrep "Execute '$sh1' as a 'shell' test." output
            rlAssertGrep "Execute '$bl1' as a 'shell' test." output
            # Explicit framework in test should always override default
            rlAssertGrep "Execute '$sh2' as a 'shell' test." output
            rlAssertGrep "Execute '$bl2' as a 'beakerlib' test." output
            # Beakerlib dependency should be detected from framework
            rlAssertGrep "dnf install.*beakerlib" output
        rlPhaseEnd
    done

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
