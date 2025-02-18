import pytest


def pytest_addoption(parser):
    parser.addoption("--functional", action="store_true",
                     help="run the functional tests (marked with marker @functional)")


def pytest_runtest_setup(item):
    if 'functional' in item.keywords and not item.config.getoption("--functional"):
        pytest.skip("need --functional option to run this test")
