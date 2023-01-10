import dataclasses
from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

import tmt.log
import tmt.utils
from tmt.utils import (SerializableContainer, dataclass_field_by_name,
                       dataclass_field_metadata, dataclass_normalize_field,
                       field)


def test_sanity():
    pass


def test_field_normalize_callback(root_logger: tmt.log.Logger) -> None:
    def _normalize_foo(raw_value: Any, logger: tmt.log.Logger) -> int:
        if raw_value is None:
            return None

        try:
            return int(raw_value)

        except ValueError as exc:
            raise tmt.utils.SpecificationError(
                "Field 'foo' can be either unset or integer,"
                f" '{type(raw_value).__name__}' found.") from exc

    @dataclasses.dataclass
    class DummyContainer(SerializableContainer):
        foo: Optional[int] = field(
            default=1,
            normalize=_normalize_foo
            )

    # Initialize a data package
    data = DummyContainer()
    assert data.foo == 1

    dataclass_normalize_field(data, 'foo', None, root_logger)
    assert data.foo is None

    dataclass_normalize_field(data, 'foo', 2, root_logger)
    assert data.foo == 2

    dataclass_normalize_field(data, 'foo', '3', root_logger)
    assert data.foo == 3

    with pytest.raises(
            tmt.utils.SpecificationError,
            match=r"Field 'foo' can be either unset or integer, 'str' found."):
        dataclass_normalize_field(data, 'foo', 'will crash', root_logger)

    assert data.foo == 3


def test_field_normalize_special_method(root_logger: tmt.log.Logger) -> None:
    def normalize_foo(cls, raw_value: Any, logger: tmt.log.Logger) -> int:
        if raw_value is None:
            return None

        try:
            return int(raw_value)

        except ValueError as exc:
            raise tmt.utils.SpecificationError(
                "Field 'foo' can be either unset or integer,"
                f" '{type(raw_value).__name__}' found.") from exc

    @dataclasses.dataclass
    class DummyContainer(SerializableContainer):
        foo: Optional[int] = field(
            default=1
            )

        _normalize_foo = normalize_foo

    # Initialize a data package
    data = DummyContainer()
    assert data.foo == 1

    dataclass_normalize_field(data, 'foo', None, root_logger)
    assert data.foo is None

    dataclass_normalize_field(data, 'foo', 2, root_logger)
    assert data.foo == 2

    dataclass_normalize_field(data, 'foo', '3', root_logger)
    assert data.foo == 3

    with pytest.raises(
            tmt.utils.SpecificationError,
            match=r"Field 'foo' can be either unset or integer, 'str' found."):
        dataclass_normalize_field(data, 'foo', 'will crash', root_logger)

    assert data.foo == 3


def test_normalize_callback_preferred(root_logger: tmt.log.Logger) -> None:
    @dataclasses.dataclass
    class DummyContainer(SerializableContainer):
        foo: Optional[int] = field(default=1)

        _normalize_foo = MagicMock()

    data = DummyContainer()
    foo_metadata = dataclass_field_metadata(dataclass_field_by_name(data, 'foo'))

    foo_metadata.normalize_callback = MagicMock()

    dataclass_normalize_field(data, 'foo', 'will crash', root_logger)

    foo_metadata.normalize_callback.assert_called_once_with('will crash', root_logger)
    data._normalize_foo.assert_not_called()
