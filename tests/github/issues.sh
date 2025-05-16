#!/bin/bash
. /usr/share/beakerlib/beakerlib.sh || exit 1

did="did --config"

YEAR_2021="--since 2021-01-01 --until 2021-12-31"
YEAR_2022="--since 2022-01-01 --until 2022-12-31"
YEAR_2023="--since 2023-01-01 --until 2023-12-31"
CHECK_UNTIL="--since 2022-10-01 --until 2022-10-26"

rlJournalStart

    # Issues Created

    rlPhaseStartTest "Issues Created"
        rlRun -s "$did ./config-default.ini --gh-issues-created $YEAR_2022"
        rlAssertGrep "Issues created on gh: 31$" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1737 - Introduce a new step for cleanup tasks" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#149 - Checkout of the default branch fails" $rlRun_LOG
        rlAssertGrep "packit/packit-service#1645 - Manually trigger internal jobs" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Created (org:teemtee)"
        rlRun -s "$did ./config-org.ini --gh-issues-created $YEAR_2022"
        rlAssertGrep "Issues created on gh: 30$" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1737 - Introduce a new step for cleanup tasks" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#149 - Checkout of the default branch fails" $rlRun_LOG
        rlAssertNotGrep "packit/packit-service#1645 - Manually trigger internal jobs" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Created (org:teemtee,packit)"
        rlRun -s "$did ./config-more.ini --gh-issues-created $YEAR_2023"
        rlAssertGrep "Issues created on gh: 33$" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#2493 - Implement retry functionality" $rlRun_LOG
        rlAssertGrep "packit/packit#1989 - Mention branch name" $rlRun_LOG
        rlAssertNotGrep "readthedocs/sphinx_rtd_theme#1525 - Left menu" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Created (repo:teemtee/fmf)"
        rlRun -s "$did ./config-repo.ini --gh-issues-created $YEAR_2022"
        rlAssertGrep "Issues created on gh: 2$" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#1737 - Introduce a new step for cleanup tasks" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#149 - Checkout of the default branch fails" $rlRun_LOG
        rlAssertNotGrep "packit/packit-service#1645 - Manually trigger internal jobs" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Created (user:psss)"
        rlRun -s "$did ./config-user.ini --gh-issues-created $YEAR_2021"
        rlAssertGrep "Issues created on gh: 1$" $rlRun_LOG
        rlAssertGrep "psss/did#247 - Implement pagination for the GitHub plugin" $rlRun_LOG
        rlAssertNotGrep "packit/packit#1386 - Allow to disable web access" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#910 - Shall we introduce a uuid for tests?" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Created, check correct --until"
        rlRun -s "$did ./config-default.ini --gh-issues-created $CHECK_UNTIL"
        rlAssertGrep "Issues created on gh: 1$" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#1559 - Update the overview of essential classes$" $rlRun_LOG
        rlAssertNotGrep 'teemtee/tmt#1648' $rlRun_LOG
        rlAssertNotGrep 'teemtee/tmt#1650' $rlRun_LOG
    rlPhaseEnd

    # Issues Closed

    rlPhaseStartTest "Issues Closed"
        rlRun -s "$did ./config-default.ini --gh-issues-closed $YEAR_2022"
        rlAssertGrep "Issues closed on gh: 17$" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#014 - Define a way how to undefine an attribute" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#991 - Incompatible environment variable name" $rlRun_LOG
        rlAssertGrep "psss/did#269 - Invalid plugin type 'google'" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Closed (org:teemtee)"
        rlRun -s "$did ./config-org.ini --gh-issues-closed $YEAR_2022"
        rlAssertGrep "Issues closed on gh: 15$" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#014 - Define a way how to undefine an attribute" $rlRun_LOG
        rlAssertGrep "teemtee/tmt#991 - Incompatible environment variable name" $rlRun_LOG
        rlAssertNotGrep "psss/did#269 - Invalid plugin type 'google'" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Closed (repo:teemtee/fmf)"
        rlRun -s "$did ./config-repo.ini --gh-issues-closed $YEAR_2022"
        rlAssertGrep "Issues closed on gh: 3$" $rlRun_LOG
        rlAssertGrep "teemtee/fmf#014 - Define a way how to undefine an attribute" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#991 - Incompatible environment variable name" $rlRun_LOG
        rlAssertNotGrep "psss/did#269 - Invalid plugin type 'google'" $rlRun_LOG
    rlPhaseEnd

    rlPhaseStartTest "Issues Closed (user:psss)"
        rlRun -s "$did ./config-user.ini --gh-issues-closed $YEAR_2022"
        rlAssertGrep "Issues closed on gh: 1$" $rlRun_LOG
        rlAssertNotGrep "teemtee/fmf#014 - Define a way how to undefine an attribute" $rlRun_LOG
        rlAssertNotGrep "teemtee/tmt#991 - Incompatible environment variable name" $rlRun_LOG
        rlAssertGrep "psss/did#269 - Invalid plugin type 'google'" $rlRun_LOG
    rlPhaseEnd

rlJournalEnd
