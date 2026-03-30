import pytest
from _pytest.config.argparsing import Parser
from _pytest.nodes import Item


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--functional",
        action="store_true",
        help="run the functional tests (marked with marker @functional)")

    parser.addoption(
        "--no-google",
        action="store_true",
        help="disable the google tests (require the google module)")


def pytest_ignore_collect(collection_path, config) -> bool:
    if collection_path.name == "test_google.py" and config.getoption("--no-google"):
        return True
    return False


def pytest_runtest_setup(item: Item) -> None:
    if 'functional' in item.keywords and not item.config.getoption("--functional"):
        pytest.skip("need --functional option to run this test")
