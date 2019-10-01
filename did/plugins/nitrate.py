# coding: utf-8
"""
Nitrate stats such as created test plans, runs, cases

Config example::

    [nitrate]
    type = nitrate
"""

from did.stats import Stats, StatsGroup
from did.utils import log

TEST_CASE_COPY_TAG = "TestCaseCopy"


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Nitrate Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class TestPlans(Stats):
    """ Test plans created """
    def fetch(self):
        import nitrate
        log.info("Searching for test plans created by {0}".format(self.user))
        self.stats.extend(nitrate.TestPlan.search(
            is_active=True,
            author__email=self.user.email,
            create_date__gt=str(self.options.since),
            create_date__lt=str(self.options.until)))


class TestRuns(Stats):
    """ Test runs finished """
    def fetch(self):
        import nitrate
        log.info("Searching for test runs finished by {0}".format(self.user))
        self.stats.extend(nitrate.TestRun.search(
            default_tester__email=self.user.email,
            stop_date__gt=str(self.options.since),
            stop_date__lt=str(self.options.until)))


class AutomatedCases(Stats):
    """ Automated cases created """
    def fetch(self):
        self.stats = [
            case for case in self.parent.cases
            if case.automated and case not in self.parent.copies]


class AutoproposedCases(Stats):
    """ Cases proposed for automation """
    def fetch(self):
        self.stats = [
            case for case in self.parent.cases
            if case.autoproposed and not case.automated and
                case not in self.parent.copies]


class ManualCases(Stats):
    """ Manual cases created """
    def fetch(self):
        self.stats = [
            case for case in self.parent.cases
            if not case.automated and case not in self.parent.copies]


class CopiedCases(Stats):
    """ Test cases copied """
    def fetch(self):
        self.stats = self.parent.copies[:]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Stats Group
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class NitrateStats(StatsGroup):
    """ Nitrate stats """

    # Default order
    order = 100

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)
        self._cases = self._copies = None
        self.stats = [
            TestPlans(option=option + "-plans", parent=self),
            TestRuns(option=option + "-runs", parent=self),
            AutomatedCases(option=option + "-automated", parent=self),
            ManualCases(option=option + "-manual", parent=self),
            AutoproposedCases(option=option + "-proposed", parent=self),
            CopiedCases(option=option + "-copied", parent=self),
            ]

    @property
    def cases(self):
        """ All test cases created by the user """
        import nitrate
        if self._cases is None:
            log.info("Searching for cases created by {0}".format(self.user))
            self._cases = [
                case for case in nitrate.TestCase.search(
                    author__email=self.user.email,
                    create_date__gt=str(self.options.since),
                    create_date__lt=str(self.options.until))
                if case.status != nitrate.CaseStatus("DISABLED")]
        return self._cases

    @property
    def copies(self):
        """ All test case copies created by the user """
        import nitrate
        if self._copies is None:
            log.info("Searching for cases copied by {0}".format(self.user))
            self._copies = [
                case for case in nitrate.TestCase.search(
                    author__email=self.user.email,
                    create_date__gt=str(self.options.since),
                    create_date__lt=str(self.options.until),
                    tag__name=TEST_CASE_COPY_TAG)]
        return self._copies
