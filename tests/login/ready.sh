#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

rlJournalStart
    rlPhaseStartSetup
        rlRun "pushd data"
    rlPhaseEnd

    for method in ${METHODS:-virtual}; do
        rlPhaseStartTest "Positive login test for ($method)"
            rlRun -s "tmt run -a provision -h $method login -c exit" 0-255
            rlAssertGrep "login: Starting interactive shell" "$rlRun_LOG"
        rlPhaseEnd

        if [[ $method == "virtual" ]]; then
            image_url="FOOOOO"
            rlPhaseStartTest "Negative login test for $method (image url = $image_url)"
                rlRun -s "tmt run -a provision -h $method -i $image_url login -c exit" 0-255 \
                    "disallowed to login into guest which is virtual if image url is invalid"
                rlAssertNotGrep "login: Starting interactive shell" "$rlRun_LOG"
                rlAssertGrep "Could not map.*to compose" "$rlRun_LOG"
            rlPhaseEnd

            image_url="file:///rubbish"
            rlPhaseStartTest "Negative login test for $method (image url = $image_url)"
                rlRun -s "tmt run -a provision -h $method -i $image_url login -c exit" 0-255 \
                    "disallowed to login into guest which is virtual if image url is invalid"
                rlAssertNotGrep "login: Starting interactive shell" "$rlRun_LOG"
                rlAssertGrep "Image .*rubbish' not found" "$rlRun_LOG"
            rlPhaseEnd
        fi
    done

    rlPhaseStartCleanup
        rlRun "popd"
    rlPhaseEnd
rlJournalEnd
