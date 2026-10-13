#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

did="did --config"

YEAR_2022="--since 2022-01-01 --until 2022-12-31"
YEAR_2021="--since 2021-01-01 --until 2021-12-31"
CHECK_UNTIL="--since 2022-10-01 --until 2022-10-26"
WEEK_41="--since 2026-10-05 --until 2026-10-11"

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

    # Pull Requests Reviewed
    #
    # Reviewed pull requests are counted by the date the review was
    # submitted, not by the date the pull request was closed. These
    # assertions guard that behavior using the week 41/2026 data:
    #
    #   * pull requests reviewed in the window but closed later (or still
    #     open) must be included, even though the old `closed:` qualifier
    #     missed them (tmt#5203, tmt#5200, did#478, did#475),
    #   * pull requests closed in the window but reviewed earlier must be
    #     excluded, even though the old qualifier counted them (did#469).
    #
    # Note: the reviewed stat fetches reviews per pull request, so a token
    # is needed to avoid hitting the unauthenticated rate limit.

    rlPhaseStartTest "Pull Requests Reviewed"
        rlRun -s "$did ./config-default.ini --gh-pull-requests-reviewed $WEEK_41"
        rlAssertGrep "Pull requests reviewed on gh: 12$" $rlRun_LOG
        # Baseline reviews present with either implementation
        rlAssertGrep "teemtee/tmt#5217 - Note the real purpose of" $rlRun_LOG
        rlAssertGrep "psss/did#484 - Skip live Pagure tests after the" $rlRun_LOG
        # Reviewed in the window but closed later or still open (newly counted)
        rlAssertGrep "teemtee/tmt#5203 - Update renovatebot image" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#5200 - Update GitHub Actions" $rlRun_LOG
        rlAssertGrep "psss/did#478 - Add CLAUDE.md project guidance" $rlRun_LOG
        rlAssertGrep "psss/did#475 - Add Jira sprint support for" $rlRun_LOG
        # Closed in the window but reviewed earlier (no longer counted)
        rlAssertNotGrep "psss/did#469 - Support fetching tokens" $rlRun_LOG
    rlPhaseEnd

rlJournalEnd
