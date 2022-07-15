#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "tmp=\$(mktemp -d)" 0 "Create tmp directory"
        rlRun "cp -r $(git rev-parse --show-toplevel)/examples/plugins $tmp"
        rlRun "pushd $tmp"

        # For local development this can run already in venv, do not use venv
        if rpm -qf $(command -v python3); then
            USE_VENV=true
            rlRun "python3 -m venv --system-site-package venv"
            # To get venv's entry_point properly
            tmt="python3 \$(which tmt)"
        else
            USE_VENV=false
            tmt=tmt
        fi
    rlPhaseEnd

    rlPhaseStartTest "Using entry_points"
        $USE_VENV && rlRun "source venv/bin/activate"

        # Plugins are not available before
        rlRun -s "$tmt run discover -h example --help" "2"
        rlAssertGrep "Unsupported discover method" "$rlRun_LOG"
        rlRun -s "$tmt run provision -h example --help" "2"
        rlAssertGrep "Unsupported provision method" "$rlRun_LOG"

        # Install them to entry_point and they work now
        rlRun "pip install ./plugins"
        rlRun "$tmt run discover -h example --help"
        rlRun "$tmt run provision -h example --help"

        # Uninstall them
        rlRun "pip uninstall -y demo-plugins"

        $USE_VENV && rlRun "deactivate"
    rlPhaseEnd

    rlPhaseStartTest "Using TMT_PLUGINS"
        # setup.py is not a plugin and cannot be loaded
        rlRun "mv ./plugins/setup.py ./plugins/setup.XXX"

        # Plugins are not available before
        rlRun -s "$tmt run discover -h example --help" "2"
        rlAssertGrep "Unsupported discover method" "$rlRun_LOG"
        rlRun -s "$tmt run provision -h example --help" "2"
        rlAssertGrep "Unsupported provision method" "$rlRun_LOG"

        # Export variable and plugins work now
        rlRun "export TMT_PLUGINS=./plugins"
        rlRun "$tmt run discover -h example --help"
        rlRun "$tmt run provision -h example --help"

        rlRun "unset TMT_PLUGINS"
        rlRun "mv ./plugins/setup.XXX ./plugins/setup.py"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $tmp" 0 "Remove tmp directory"
    rlPhaseEnd
rlJournalEnd
