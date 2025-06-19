# coding: utf-8

from typing import Optional

import pytest

import did.base
import did.stats

MISSING_TYPE_CONFIG = f"""{did.base.Config.example()}
[broken]
first = test
"""

EMPTY_CONFIG = f"""{did.base.Config.example()}

[empty_group]
type = empty
first_empty_stat = First Empty
second_empty_stat = Second Empty
"""


class MyTestStats(did.stats.Stats):
    """My Test Stat Class
    useless line, just checking name
    """

    def fetch(self) -> None:
        self.stats = [f"Fetched {self.option}"]


class MyTestStatsGroup(did.stats.StatsGroup):
    """My Test StatsGroup Class
    useless line, just checking name
    """

    def __init__(self,
                 option: str,
                 name: Optional[str] = None,
                 parent: Optional[did.stats.StatsGroup] = None,
                 user: Optional[did.base.User] = None) -> None:
        did.stats.StatsGroup.__init__(self, option, name, parent, user)

    def check(self) -> None:
        self.stats = [
            MyTestStats("first"),
            MyTestStats("second"),
            ]
        super().check()


def test_stats_class(capsys: pytest.CaptureFixture[str]) -> None:
    mystat = did.stats.Stats("test_stat")
    assert mystat.name == "General statistics"
    with pytest.raises(NotImplementedError):
        mystat.fetch()

    mystat = MyTestStats("test_stat")
    assert mystat.name == "My Test Stat Class"

    mystat = MyTestStats("test_stat", name="My Stats")
    assert mystat.name == "My Stats"
    assert mystat.enabled()
    mystat.show()
    captured = capsys.readouterr()
    assert captured.out == ""
    mystat.check()
    mystat.show()
    captured = capsys.readouterr()
    assert captured.out == "* My Stats: 1\n    * Fetched test_stat\n"

    additional_stat = MyTestStats("test_stat")
    additional_stat.stats = ["This is another stat"]
    mystat.merge(additional_stat)
    mystat.show()
    captured = capsys.readouterr()
    assert captured.out == (
        "* My Stats: 2\n"
        "    * Fetched test_stat\n"
        "    * This is another stat\n")
    assert not mystat.error
    additional_stat.error = True
    mystat.merge(additional_stat)
    assert mystat.error


def test_statsgroup_class(capsys: pytest.CaptureFixture[str]) -> None:
    mystatgroup = did.stats.StatsGroup("test_group")
    assert mystatgroup.name == "Stats group"
    mystatgroup.fetch()

    mystatgroup = MyTestStatsGroup("test_statgroup")
    assert mystatgroup.name == "My Test StatsGroup Class"
    mystatgroup = MyTestStatsGroup("test_statgroup", name="My StatsGroup")
    assert mystatgroup.name == "My StatsGroup"
    assert mystatgroup.enabled()
    mystatgroup.show()
    captured = capsys.readouterr()
    assert captured.out == ""
    mystatgroup.check()
    mystatgroup.show()
    captured = capsys.readouterr()
    assert captured.out == (
        "* My Test Stat Class: 1\n"
        "    * Fetched first\n"
        "* My Test Stat Class: 1\n"
        "    * Fetched second\n")

    additional_stat = MyTestStatsGroup("test_statgroup")
    additional_stat.stats = [
        MyTestStats("additional_one"),
        MyTestStats("additional_two"),
        ]
    additional_stat.stats[0].stats = ["Additional One"]
    additional_stat.stats[1].stats = ["Additional Two"]
    mystatgroup.merge(additional_stat)
    mystatgroup.show()
    captured = capsys.readouterr()
    assert captured.out == (
        "* My Test Stat Class: 2\n"
        "    * Fetched first\n"
        "    * Additional One\n"
        "* My Test Stat Class: 2\n"
        "    * Fetched second\n"
        "    * Additional Two\n")

    assert not mystatgroup.error
    additional_stat.stats[0].error = True
    mystatgroup.merge(additional_stat)
    assert mystatgroup.error


def test_userstats_missing_type() -> None:
    config = did.base.Config(MISSING_TYPE_CONFIG)
    with pytest.raises(did.base.ConfigError):
        did.stats.UserStats(
            user=did.base.User(email=config.email),
            config=config)


def test_userstats_unknown_type() -> None:
    config = did.base.Config(EMPTY_CONFIG)
    with pytest.raises(did.base.ConfigError):
        did.stats.UserStats(
            user=did.base.User(email=config.email),
            config=config)


def test_userstats_invalid_order() -> None:
    config = did.base.Config(f"{EMPTY_CONFIG}\norder=invalid\n")
    did.stats.StatsGroupPlugin.registry["empty"] = MyTestStatsGroup
    with pytest.raises(did.base.GeneralError):
        did.stats.UserStats(
            user=did.base.User(email=config.email),
            config=config)


def test_userstats_class(capsys: pytest.CaptureFixture[str]) -> None:
    config = did.base.Config(EMPTY_CONFIG)

    did.stats.StatsGroupPlugin.registry["empty"] = MyTestStatsGroup
    ustat = did.stats.UserStats(user=did.base.User(email=config.email), config=config)
    ustat.check()
    ustat.show()
    captured = capsys.readouterr()
    assert captured.out == (
        "* My Test Stat Class: 1\n"
        "    * Fetched first\n"
        "* My Test Stat Class: 1\n"
        "    * Fetched second\n")


def test_emptystats_class(capsys: pytest.CaptureFixture[str]) -> None:
    empty = did.stats.EmptyStats("empty_stat")
    empty.fetch()
    empty.show()
    captured = capsys.readouterr()
    assert captured.out == "* Custom stats group for header & footer\n"
    nothing = did.stats.EmptyStats("empty_stat", "nothing")
    nothing.show()
    captured = capsys.readouterr()
    assert captured.out == "* nothing\n"


def test_emptystatsgroup_class(capsys: pytest.CaptureFixture[str]) -> None:
    did.base.Config(EMPTY_CONFIG)
    empty = did.stats.EmptyStatsGroup("empty_group")
    empty.fetch()
    empty.show()
    captured = capsys.readouterr()
    assert captured.out == "* First Empty\n* Second Empty\n"
