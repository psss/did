#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "output=\$(mktemp)" 0 "Create output file"
        rlRun "set -o pipefail"
        rlRun "pushd data"
    rlPhaseEnd

    # Select by name
    for tmt in 'tmt test ls' 'tmt test show'; do
        rlPhaseStartTest "$tmt"
            rlRun "$tmt | tee $output"
            rlAssertGrep "/tests/enabled/default" $output
            rlAssertGrep "/tests/tag/default" $output
            rlAssertGrep "/tests/tier/default" $output
        rlPhaseEnd

        rlPhaseStartTest "$tmt <name>"
            rlRun "$tmt tier | tee $output"
            rlAssertNotGrep "/tests/enabled/default" $output
            rlAssertNotGrep "/tests/tag/default" $output
            rlAssertGrep "/tests/tier/default" $output
        rlPhaseEnd

        rlPhaseStartTest "$tmt non-existent"
            rlRun "$tmt non-existent | tee $output"
            rlRun "[[ $(wc -l <$output) == 0 ]]" 0 "Check no output"
        rlPhaseEnd
    done

    for name in '-n' '--name'; do
        rlPhaseStartTest "tmt run test $name <name>"
            tmt='tmt run -rv discover'
            # Existing
            rlRun "$tmt test $name enabled | tee $output"
            rlAssertGrep "/tests/enabled/default" $output
            rlAssertNotGrep "/tests/enabled/disabled" $output
            rlAssertNotGrep "/tests/tag/default" $output
            rlAssertNotGrep "/tests/tier/default" $output
            # Missing
            rlRun "$tmt test $name non-existent | tee $output"
            rlAssertGrep "No tests found" $output
            # Using 'test --name' overrides 'test' in discover
            rlRun "$tmt test $name tier/one | tee $output"
            rlAssertGrep "/tests/tier/one" $output
            rlAssertNotGrep "/tests/tier/two" $output
        rlPhaseEnd
    done

    rlPhaseStartTest "Select tests using a filter"
        # Enabled
        for bool in True true; do
            rlRun "tmt test ls --filter enabled:$bool | tee $output"
            rlAssertGrep '/tests/enabled/default' $output
            rlAssertGrep '/tests/enabled/defined' $output
            rlAssertNotGrep '/tests/enabled/disabled' $output
        done
        for bool in False false; do
            rlRun "tmt test ls --filter enabled:False | tee $output"
            rlAssertNotGrep '/tests/enabled/default' $output
            rlAssertNotGrep '/tests/enabled/defined' $output
            rlAssertGrep '/tests/enabled/disabled' $output
        done

        for tmt in 'tmt test ls' 'tmt run -rv discover test' \
            'tmt run -rv plans --name /plans/filtered discover test'; do
            # Tag
            rlRun "$tmt --filter tag:slow | tee $output"
            rlAssertNotGrep '/tests/tag/default' $output
            rlAssertGrep '/tests/tag/defined' $output
            rlAssertNotGrep '/tests/tag/empty' $output
            rlRun "$tmt --filter tag:-slow | tee $output"
            rlAssertGrep '/tests/enabled/default' $output
            rlAssertNotGrep '/tests/tag/defined' $output
            rlAssertGrep '/tests/tag/empty' $output

            # Tier
            rlRun "$tmt --filter tier:1 | tee $output"
            rlAssertGrep '/tests/tier/one' $output
            rlAssertNotGrep '/tests/tier/two' $output
            rlAssertNotGrep '/tests/tier/default' $output
            rlRun "$tmt --filter tier:-1 | tee $output"
            rlAssertNotGrep '/tests/tier/one' $output
            rlAssertGrep '/tests/tier/two' $output
            rlAssertGrep '/tests/tier/default' $output
            rlRun "$tmt --filter tier:1,2 | tee $output"
            rlAssertGrep '/tests/tier/one' $output
            rlAssertGrep '/tests/tier/two' $output
            rlAssertNotGrep '/tests/tier/default' $output
            rlRun "$tmt -f tier:-1 -f tier:-2 | tee $output"
            rlAssertNotGrep '/tests/tier/one' $output
            rlAssertNotGrep '/tests/tier/two' $output
            rlAssertGrep '/tests/tier/default' $output
        done
    rlPhaseEnd

    rlPhaseStartTest "Select tests using a condition"
        # Enabled
        rlRun "tmt test ls --condition 'enabled == True' | tee $output"
        rlAssertGrep '/tests/enabled/default' $output
        rlAssertGrep '/tests/enabled/defined' $output
        rlAssertNotGrep '/tests/enabled/disabled' $output
        rlRun "tmt test ls --condition 'enabled == False' | tee $output"
        rlAssertNotGrep '/tests/enabled/default' $output
        rlAssertNotGrep '/tests/enabled/defined' $output
        rlAssertGrep '/tests/enabled/disabled' $output

        for tmt in 'tmt test ls' 'tmt run -rv discover test'; do
            # Tag
            rlRun "$tmt --condition '\"slow\" in tag' | tee $output"
            rlAssertNotGrep '/tests/tag/default' $output
            rlAssertGrep '/tests/tag/defined' $output
            rlAssertNotGrep '/tests/tag/empty' $output
            rlRun "$tmt --condition '\"slow\" not in tag' | tee $output"
            rlAssertGrep '/tests/enabled/default' $output
            rlAssertNotGrep '/tests/tag/defined' $output
            rlAssertGrep '/tests/tag/empty' $output

            # Tier
            rlRun "$tmt --condition 'tier is not None' | tee $output"
            rlAssertGrep '/tests/tier/one' $output
            rlAssertGrep '/tests/tier/two' $output
            rlAssertNotGrep '/tests/tier/default' $output
            rlRun "$tmt -c 'tier and int(tier) > 1' | tee $output"
            rlAssertNotGrep '/tests/tier/one' $output
            rlAssertGrep '/tests/tier/two' $output
            rlAssertNotGrep '/tests/tier/default' $output
        done
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm $output" 0 "Remove output file"
    rlPhaseEnd
rlJournalEnd
