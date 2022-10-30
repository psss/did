import logging

import _pytest.logging
import pytest

from tmt.log import (DebugLevelFilter, Logger, QuietnessFilter,
                     VerbosityLevelFilter)

from . import assert_log


def test_sanity(caplog: _pytest.logging.LogCaptureFixture, root_logger: Logger) -> None:
    root_logger.print('this is printed')
    root_logger.debug('this is a debug message')
    root_logger.verbose('this is a verbose message')
    root_logger.info('this is just an info')
    root_logger.warn('this is a warning')
    root_logger.fail('this is a failure')

    assert_log(caplog, details_key='this is printed', levelno=logging.INFO)
    assert_log(caplog, details_key='this is a debug message', levelno=logging.DEBUG)
    assert_log(caplog, details_key='this is a verbose message', levelno=logging.INFO)
    assert_log(caplog, details_key='this is just an info', levelno=logging.INFO)
    assert_log(caplog, details_key='warn', details_value='this is a warning', levelno=logging.WARN)
    assert_log(
        caplog,
        details_key='fail',
        details_value='this is a failure',
        levelno=logging.ERROR)


def test_creation(caplog: _pytest.logging.LogCaptureFixture, root_logger: Logger) -> None:
    logger = Logger.create()
    assert logger._logger.name == 'tmt'

    actual_logger = logging.Logger('3rd-party-app-logger')
    logger = Logger.create(actual_logger)
    assert logger._logger is actual_logger


def test_descend(caplog: _pytest.logging.LogCaptureFixture, root_logger: Logger) -> None:
    deeper_logger = root_logger.descend().descend().descend()

    deeper_logger.print('this is printed')
    deeper_logger.debug('this is a debug message')
    deeper_logger.verbose('this is a verbose message')
    deeper_logger.info('this is just an info')
    deeper_logger.warn('this is a warning')
    deeper_logger.fail('this is a failure')

    assert_log(caplog, details_key='this is printed', levelno=logging.INFO)
    assert_log(caplog, details_key='this is a debug message', levelno=logging.DEBUG)
    assert_log(caplog, details_key='this is a verbose message', levelno=logging.INFO)
    assert_log(caplog, details_key='this is just an info', levelno=logging.INFO)
    assert_log(caplog, details_key='warn', details_value='this is a warning', levelno=logging.WARN)
    assert_log(
        caplog,
        details_key='fail',
        details_value='this is a failure',
        levelno=logging.ERROR)


@pytest.mark.parametrize(
    ('logger_verbosity', 'message_verbosity', 'filter_outcome'),
    [
        # (
        #   logger verbosity - corresponds to -v, -vv, -vvv CLI options,
        #   message verbosity - `level` parameter of `verbosity(...)` call,
        #   expected outcome of `VerbosityLevelFilter.filter()` - returns integer!
        # )
        (0, 1, 0),
        (1, 1, 1),
        (2, 1, 1),
        (3, 1, 1),
        (4, 1, 1),
        (0, 2, 0),
        (1, 2, 0),
        (2, 2, 1),
        (3, 2, 1),
        (4, 2, 1),
        (0, 3, 0),
        (1, 3, 0),
        (2, 3, 0),
        (3, 3, 1),
        (4, 3, 1),
        (0, 4, 0),
        (1, 4, 0),
        (2, 4, 0),
        (3, 4, 0),
        (4, 4, 1)
        ]
    )
def test_verbosity_filter(
        logger_verbosity: int,
        message_verbosity: int,
        filter_outcome: int
        ) -> None:
    filter = VerbosityLevelFilter()

    assert filter.filter(logging.makeLogRecord({
        'levelno': logging.INFO,
        'details': {
            'logger_verbosity_level': logger_verbosity,
            'message_verbosity_level': message_verbosity
            }
        })) == filter_outcome


@pytest.mark.parametrize(
    ('logger_debug', 'message_debug', 'filter_outcome'),
    [
        # (
        #   logger debug level - corresponds to -d, -dd, -ddd CLI options,
        #   message debug level - `level` parameter of `debug(...)` call,
        #   expected outcome of `DebugLevelFilter.filter()` - returns integer!
        # )
        (0, 1, 0),
        (1, 1, 1),
        (2, 1, 1),
        (3, 1, 1),
        (4, 1, 1),
        (0, 2, 0),
        (1, 2, 0),
        (2, 2, 1),
        (3, 2, 1),
        (4, 2, 1),
        (0, 3, 0),
        (1, 3, 0),
        (2, 3, 0),
        (3, 3, 1),
        (4, 3, 1),
        (0, 4, 0),
        (1, 4, 0),
        (2, 4, 0),
        (3, 4, 0),
        (4, 4, 1)
        ]
    )
def test_debug_filter(
        logger_debug: int,
        message_debug: int,
        filter_outcome: int
        ) -> None:
    filter = DebugLevelFilter()

    assert filter.filter(logging.makeLogRecord({
        'levelno': logging.DEBUG,
        'details': {
            'logger_debug_level': logger_debug,
            'message_debug_level': message_debug
            }
        })) == filter_outcome


@pytest.mark.parametrize(
    ('levelno', 'filter_outcome'),
    [
        # (
        #   log message level,
        #   expected outcome of `QietnessFilter.filter()` - returns integer!
        # )
        (logging.DEBUG, 0),
        (logging.INFO, 0),
        (logging.WARNING, 1),
        (logging.ERROR, 1),
        (logging.CRITICAL, 1)
        ]
    )
def test_quietness_filter(levelno: int, filter_outcome: int) -> None:
    filter = QuietnessFilter()

    assert filter.filter(logging.makeLogRecord({
        'levelno': levelno
        })) == filter_outcome
