#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

did="did --config"

YEAR_2022="--since 2022-01-01 --until 2022-12-31"
YEAR_2021="--since 2021-01-01 --until 2021-12-31"
CHECK_UNTIL="--since 2022-10-01 --until 2022-10-26"

rlJournalStart

    # Pull Requests Created

    rlPhaseStartTest "Pull Requests Created"
        rlRun -s "$did ./config-default.ini --gh-pull-requests-created $YEAR_2022"
        rlAssertGrep "Pull requests created on gh: 94$" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1750 - Include the new web link in verbose" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#170 - Implement a directive for disabling inheritance" $rlRun_LOG
        rlAssertGrep "teemtee/try#002 - Check logs for test with a hash sign in" $rlRun_LOG
        rlAssertGrep "psss/did#275 - Speed up local testing" $rlRun_LOG
        rlAssertGrep "psss/python-nitrate#039 - Enable basic sanity" $rlRun_LOG
        rlAssertGrep "packit/packit.dev#399 - Update \`tmt\` examples" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Created (org:teemtee)"
        rlRun -s "$did ./config-org.ini --gh-pull-requests-created $YEAR_2022"
        rlAssertGrep "Pull requests created on gh: 85$" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1750 - Include the new web link in verbose" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#170 - Implement a directive for disabling inheritance" $rlRun_LOG
        rlAssertGrep "teemtee/try#002 - Check logs for test with a hash sign in" $rlRun_LOG
        rlAssertNotGrep "psss/did#275 - Speed up local testing" $rlRun_LOG
        rlAssertNotGrep "psss/python-nitrate#039 - Enable basic sanity" $rlRun_LOG
        rlAssertNotGrep "packit/packit.dev#399 - Update \`tmt\` examples" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Created (org:teemtee,packit)"
        rlRun -s "$did ./config-more.ini --gh-pull-requests-created $YEAR_2022"
        rlAssertGrep "Pull requests created on gh: 86$" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1750 - Include the new web link in verbose" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#170 - Implement a directive for disabling inheritance" $rlRun_LOG
        rlAssertGrep "teemtee/try#002 - Check logs for test with a hash sign in" $rlRun_LOG
        rlAssertNotGrep "psss/did#275 - Speed up local testing" $rlRun_LOG
        rlAssertNotGrep "psss/python-nitrate#039 - Enable basic sanity" $rlRun_LOG
        rlAssertGrep "packit/packit.dev#399 - Update \`tmt\` examples" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Created (repo:teemtee/fmf)"
        rlRun -s "$did ./config-repo.ini --gh-pull-requests-created $YEAR_2022"
        rlAssertGrep "Pull requests created on gh: 7$" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#1750 - Include the new web link in verbose" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#170 - Implement a directive for disabling inheritance" $rlRun_LOG
        rlAssertNotGrep "teemtee/try#002 - Check logs for test with a hash sign in" $rlRun_LOG
        rlAssertNotGrep "psss/did#275 - Speed up local testing" $rlRun_LOG
        rlAssertNotGrep "psss/python-nitrate#039 - Enable basic sanity" $rlRun_LOG
        rlAssertNotGrep "packit/packit.dev#399 - Update \`tmt\` examples" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Created (user:psss)"
        rlRun -s "$did ./config-user.ini --gh-pull-requests-created $YEAR_2022"
        rlAssertGrep "Pull requests created on gh: 7$" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#1750 - Include the new web link in verbose" $rlRun_LOG
        rlAssertNotGrep "teemtee/fmf#170 - Implement a directive for disabling inheritance" $rlRun_LOG
        rlAssertNotGrep "teemtee/try#002 - Check logs for test with a hash sign in" $rlRun_LOG
        rlAssertGrep "psss/did#275 - Speed up local testing" $rlRun_LOG
        rlAssertGrep "psss/python-nitrate#039 - Enable basic sanity" $rlRun_LOG
        rlAssertNotGrep "packit/packit.dev#399 - Update \`tmt\` examples" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Created, check correct --until"
        rlRun -s "$did ./config-default.ini --gh-pull-requests-created $CHECK_UNTIL"
        rlAssertGrep "Pull requests created on gh: 7$" $rlRun_LOG
        rlAssertGrep 'teemtee/tmt#1642 - Move the hardware specification into a separate page$' $rlRun_LOG
        rlAssertNotGrep 'teemtee/tmt#1645' $rlRun_LOG
        rlAssertNotGrep 'teemtee/tmt#1644' $rlRun_LOG
    rlPhaseEnd

    # Pull Requests Closed

    rlPhaseStartTest "Pull Requests Closed"
        rlRun -s "$did ./config-default.ini --gh-pull-requests-closed $YEAR_2022"
        rlAssertGrep "Pull requests closed on gh: 315$" $rlRun_LOG
        rlAssertGrep "psss/did#272 - Koji plugin" $rlRun_LOG
        rlAssertGrep "psss/python-nitrate#038 - Properly handle string" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#177 - Shallow git clone if no reference" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1050 - Run commands via bash" $rlRun_LOG
        rlAssertGrep "teemtee/upgrade#006 - Store the old packages " $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Closed (org:teemtee)"
        rlRun -s "$did ./config-org.ini --gh-pull-requests-closed $YEAR_2022"
        rlAssertGrep "Pull requests closed on gh: 305$" $rlRun_LOG
        rlAssertNotGrep "psss/did#272 - Koji plugin" $rlRun_LOG
        rlAssertNotGrep "psss/python-nitrate#038 - Properly handle string" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#177 - Shallow git clone if no reference" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1050 - Run commands via bash" $rlRun_LOG
        rlAssertGrep "teemtee/upgrade#006 - Store the old packages " $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Closed (repo:teemtee/fmf)"
        rlRun -s "$did ./config-repo.ini --gh-pull-requests-closed $YEAR_2022"
        rlAssertGrep "Pull requests closed on gh: 13$" $rlRun_LOG
        rlAssertNotGrep "psss/did#272 - Koji plugin" $rlRun_LOG
        rlAssertNotGrep "psss/python-nitrate#038 - Properly handle string" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#177 - Shallow git clone if no reference" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#1050 - Run commands via bash" $rlRun_LOG
        rlAssertNotGrep "teemtee/upgrade#006 - Store the old packages " $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Pull Requests Closed (user:psss)"
        rlRun -s "$did ./config-user.ini --gh-pull-requests-closed $YEAR_2022"
        rlAssertGrep "Pull requests closed on gh: 10$" $rlRun_LOG
        rlAssertGrep "psss/did#272 - Koji plugin" $rlRun_LOG
        rlAssertGrep "psss/python-nitrate#038 - Properly handle string" $rlRun_LOG
        rlAssertNotGrep "teemtee/fmf#177 - Shallow git clone if no reference" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#1050 - Run commands via bash" $rlRun_LOG
        rlAssertNotGrep "teemtee/upgrade#006 - Store the old packages " $rlRun_LOG
    rlPhaseEnd

rlJournalEnd
