import pytest
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item


def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--functional", action="store_true",
                     help="run the functional tests (marked with marker @functional)")


def pytest_runtest_setup(item: Item) -> None:
    if 'functional' in item.keywords and not item.config.getoption("--functional"):
        pytest.skip("need --functional option to run this test")
