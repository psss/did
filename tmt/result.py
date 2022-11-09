import dataclasses
import enum
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

import click
import fmf

import tmt.utils

if TYPE_CHECKING:
    import tmt.base

# Extra keys used for identification in Result class
EXTRA_RESULT_IDENTIFICATION_KEYS = ['extra-nitrate', 'extra-task']


# TODO: this should become a more strict data class, with an enum or two to handle
# allowed values, etc. See https://github.com/teemtee/tmt/issues/1456.
# Defining a type alias so we can follow where the package is used.
class ResultOutcome(enum.Enum):
    PASS = 'pass'
    FAIL = 'fail'
    INFO = 'info'
    WARN = 'warn'
    ERROR = 'error'

    @classmethod
    def from_spec(cls, spec: str) -> 'ResultOutcome':
        try:
            return ResultOutcome(spec)
        except ValueError:
            raise tmt.utils.SpecificationError(f"Invalid partial custom result '{spec}'.")


# Cannot subclass enums :/
# https://docs.python.org/3/library/enum.html#restricted-enum-subclassing
class ResultInterpret(enum.Enum):
    # These are "inherited" from ResultOutcome
    PASS = 'pass'
    FAIL = 'fail'
    INFO = 'info'
    WARN = 'warn'
    ERROR = 'error'

    # Special interpret values
    RESPECT = 'respect'
    CUSTOM = 'custom'
    XFAIL = 'xfail'

    @classmethod
    def is_result_outcome(cls, value: 'ResultInterpret') -> bool:
        return value.name in list(ResultOutcome.__members__.keys())


RESULT_OUTCOME_COLORS: Dict[ResultOutcome, str] = {
    ResultOutcome.PASS: 'green',
    ResultOutcome.FAIL: 'red',
    ResultOutcome.INFO: 'blue',
    ResultOutcome.WARN: 'yellow',
    ResultOutcome.ERROR: 'magenta'
    }


@dataclasses.dataclass
class ResultData:
    """
    Formal data class containing information about result of the test
    """
    result: ResultOutcome
    log: List[str] = dataclasses.field(default_factory=list)
    note: Optional[str] = None
    duration: Optional[str] = None
    ids: Dict[str, Optional[str]] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(init=False)
class Result(tmt.utils.SerializableContainer):
    """
    Test result

    Required parameter 'data' needs to be type of ResultData.
    Required parameter 'test' or 'name' should contain a test reference.
    """

    name: str
    result: ResultOutcome
    note: Optional[str] = None
    duration: Optional[str] = None
    ids: Dict[str, Optional[str]] = dataclasses.field(default_factory=dict)
    log: Union[List[Any], Dict[Any, Any]] = dataclasses.field(default_factory=list)
    # TODO: Check why log can be also a Dictionary.
    # Check if we can safely get rid of Union.
    # Should be the same type as in ResultData class.
    # Check why there is a List[Any] and not a List[str]

    def __init__(
            self,
            *,
            data: ResultData,
            name: Optional[str] = None,
            test: Optional['tmt.base.Test'] = None) -> None:
        """ Initialize test result data """

        from tmt.base import Test
        super().__init__()

        # Save the test name and optional note
        if not test and not name:
            raise tmt.utils.SpecificationError(
                "Either name or test have to be specified")
        if test and not isinstance(test, Test):
            raise tmt.utils.SpecificationError(f"Invalid test '{test}'.")
        if name and not isinstance(name, str):
            raise tmt.utils.SpecificationError(f"Invalid test name '{name}'.")

        # ignore[union-attr]: either `name` or `test` is set, we just
        # made sure of it above, but mypy won't realize that.
        self.name = name or test.name  # type: ignore[union-attr]
        self.note = data.note
        self.duration = data.duration
        if test:
            # Saving identifiable information for each test case so we can match them
            # to Polarion/Nitrate/other cases and report run results there
            # TODO: would an exception be better? Can test.id be None?
            self.ids = {tmt.identifier.ID_KEY: test.id}
            for key in EXTRA_RESULT_IDENTIFICATION_KEYS:
                self.ids[key] = test.node.get(key)
            interpret = ResultInterpret(test.result) if test.result else ResultInterpret.RESPECT
        else:
            self.ids = data.ids
            interpret = ResultInterpret.RESPECT

        self.result = data.result
        self.log = data.log

        # Handle alternative result interpretation
        if interpret not in (ResultInterpret.RESPECT, ResultInterpret.CUSTOM):
            # Extend existing note or set a new one
            if self.note and isinstance(self.note, str):
                self.note += f', original result: {self.result.value}'
            elif self.note is None:
                self.note = f'original result: {self.result.value}'
            else:
                raise tmt.utils.SpecificationError(
                    f"Test result note '{self.note}' must be a string.")

            if interpret == ResultInterpret.XFAIL:
                # Swap just fail<-->pass, keep the rest as is (info, warn,
                # error)
                self.result = {
                    ResultOutcome.FAIL: ResultOutcome.PASS,
                    ResultOutcome.PASS: ResultOutcome.FAIL
                    }.get(self.result, self.result)
            elif ResultInterpret.is_result_outcome(interpret):
                self.result = ResultOutcome(interpret.value)
            else:
                raise tmt.utils.SpecificationError(
                    f"Invalid result '{interpret.value}' in test '{self.name}'.")

    @staticmethod
    def total(results: List['Result']) -> Dict[ResultOutcome, int]:
        """ Return dictionary with total stats for given results """
        stats = {result: 0 for result in RESULT_OUTCOME_COLORS}

        for result in results:
            stats[result.result] += 1
        return stats

    @staticmethod
    def summary(results: List['Result']) -> str:
        """ Prepare a nice human summary of provided results """
        stats = Result.total(results)
        comments = []
        if stats.get(ResultOutcome.PASS):
            passed = ' ' + click.style('passed', fg='green')
            comments.append(fmf.utils.listed(stats[ResultOutcome.PASS], 'test') + passed)
        if stats.get(ResultOutcome.FAIL):
            failed = ' ' + click.style('failed', fg='red')
            comments.append(fmf.utils.listed(stats[ResultOutcome.FAIL], 'test') + failed)
        if stats.get(ResultOutcome.INFO):
            count, comment = fmf.utils.listed(stats[ResultOutcome.INFO], 'info').split()
            comments.append(count + ' ' + click.style(comment, fg='blue'))
        if stats.get(ResultOutcome.WARN):
            count, comment = fmf.utils.listed(stats[ResultOutcome.WARN], 'warn').split()
            comments.append(count + ' ' + click.style(comment, fg='yellow'))
        if stats.get(ResultOutcome.ERROR):
            count, comment = fmf.utils.listed(stats[ResultOutcome.ERROR], 'error').split()
            comments.append(count + ' ' + click.style(comment, fg='magenta'))
        # FIXME: cast() - https://github.com/teemtee/fmf/issues/185
        return cast(str, fmf.utils.listed(comments or ['no results found']))

    def show(self) -> str:
        """ Return a nicely colored result with test name (and note) """
        result = 'errr' if self.result == ResultOutcome.ERROR else self.result.value
        colored = click.style(result, fg=RESULT_OUTCOME_COLORS[self.result])
        note = f" ({self.note})" if self.note else ''
        return f"{colored} {self.name}{note}"

    def to_serialized(self) -> Dict[str, Any]:
        fields = super().to_serialized()
        fields['result'] = self.result.value
        return fields

    @classmethod
    def from_serialized(cls, serialized: Dict[str, Any]) -> 'Result':
        # TODO: from_serialized() should trust the input. We should add its
        # clone to read serialized-but-from-possibly-untrustworthy-source data -
        # that's the place where the schema validation would happen in the
        # future.

        # Our special key may or may not be present, depending on who
        # calls this method.  In any case, it is not needed, because we
        # already know what class to restore: this one.
        serialized.pop('__class__', None)

        name = serialized.pop('name')
        serialized['result'] = ResultOutcome.from_spec(serialized['result'])
        return cls(data=ResultData(**serialized), name=name)

    @staticmethod
    def failures(log: Optional[str], msg_type: str = 'FAIL') -> str:
        """ Filter stdout and get only messages with certain type """
        if not log:
            return ''
        filtered = ''

        # Filter beakerlib style logs, reverse the log string by lines, search for each FAIL
        # and every associated line, then reverse the picked lines back into correct order
        for m in re.findall(
                fr'(^.*\[\s*{msg_type}\s*\][\S\s]*?)(?:^::\s+\[[0-9: ]+|:{{80}})',
                '\n'.join(log.split('\n')[::-1]), re.MULTILINE):
            filtered += m.strip() + '\n'
        if filtered:
            return '\n'.join(filtered.strip().split('\n')[::-1])

        # Check for other failures and errors when not using beakerlib
        for m in re.findall(
                fr'.*\b(?=error|fail|{msg_type})\b.*', log, re.IGNORECASE | re.MULTILINE):
            filtered += m + '\n'

        return filtered or log
