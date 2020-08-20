. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "TMP=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TMP"
        rlRun "set -o pipefail"
        rlRun "tmt init"
    rlPhaseEnd

    rlPhaseStartTest "Valid data"
        yaml1='{how: "fmf", name: "int", url: "https://int/repo"}'
        yaml2='{how: "fmf", name: "ext", url: "https://ext/repo"}'
        rlRun "tmt plan create /plans/custom --template mini \
            --discover '$yaml1' --discover '$yaml2'"
        rlAssertGrep "name: ext" "plans/custom.fmf"
        rlAssertGrep "url:.*ext/repo" "plans/custom.fmf"
    rlPhaseEnd

    rlPhaseStartTest "Valid data - fmf extension included"
        rlRun "tmt plan create plan.fmf --template mini"
        rlAssertExists "$TMP/plan.fmf"
    rlPhaseEnd

    rlPhaseStartTest "Invalid yaml"
        yaml='{how: "fmf"; name: "int"; url: "https://int/repo"}'
        rlRun "tmt plan create /plans/bad --template mini \
            --discover '$yaml' 2>&1 | tee output " 2
        rlAssertGrep "Invalid yaml data" "output"
    rlPhaseEnd

    rlPhaseStartTest "Invalid step"
        rlRun "tmt plan create /plans/bad --template mini \
            --discover '' 2>&1 | tee output " 2
        rlAssertGrep "Invalid step data" "output"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TMP" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalEnd
