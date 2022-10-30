import _pytest.logging
import pytest

from tmt.log import Logger


@pytest.fixture(name='root_logger')
def fixture_root_logger(caplog: _pytest.logging.LogCaptureFixture) -> Logger:
    return Logger.create(verbose=0, debug=0, quiet=False)
