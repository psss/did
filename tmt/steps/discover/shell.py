import copy
import dataclasses
import os
import shutil
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, cast

import click
import fmf

import tmt
import tmt.base
import tmt.steps
import tmt.steps.discover
import tmt.utils

T = TypeVar('T', bound='TestDescription')


@dataclasses.dataclass
class TestDescription(
        tmt.utils.SpecBasedContainer,
        tmt.utils.NormalizeKeysMixin,
        tmt.utils.SerializableContainer):
    """
    Keys necessary to describe a shell-based test.

    Provides basic functionality for tansition between "raw" step data representation,
    which consists of keys and values given by fmf tree and CLI options, and this
    container representation for internal use.
    """

    name: str

    # TODO: following keys are copy & pasted from base.Test. It would be much, much better
    # to re-use the definitions from base.Test instead copying them here, but base.Test
    # does not support save/load operations. This is a known issue, introduced by a patch
    # transitioning step data to data classes, it is temporary, and it will be fixed as
    # soon as possible - nobody want's to keep two very same lists of attributes.
    test: str

    # Core attributes (supported across all levels)
    summary: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    # TODO: ugly circular dependency (see tmt.base.DEFAULT_ORDER)
    order: int = 50
    link: Optional[tmt.base.Links] = None
    id: Optional[str] = None
    tag: List[str] = dataclasses.field(default_factory=list)
    tier: Optional[str] = None
    adjust: Optional[List[tmt.base._RawAdjustRule]] = None

    # Basic test information
    contact: List[str] = dataclasses.field(default_factory=list)
    component: List[str] = dataclasses.field(default_factory=list)

    # Test execution data
    path: Optional[str] = None
    framework: Optional[str] = None
    manual: bool = False
    require: List[tmt.base.Require] = dataclasses.field(default_factory=list)
    recommend: List[tmt.base.Require] = dataclasses.field(default_factory=list)
    environment: tmt.utils.EnvironmentType = dataclasses.field(default_factory=dict)
    duration: str = '1h'
    result: str = 'respect'

    _normalize_tag = tmt.utils.LoadFmfKeysMixin._normalize_string_list
    _normalize_contact = tmt.utils.LoadFmfKeysMixin._normalize_string_list
    _normalize_component = tmt.utils.LoadFmfKeysMixin._normalize_string_list

    def _normalize_order(self, value: Optional[int]) -> int:
        if value is None:
            # TODO: ugly circular dependency (see tmt.base.DEFAULT_ORDER)
            return 50
        return int(value)

    def _normalize_link(self, value: tmt.base._RawLinks) -> tmt.base.Links:
        return tmt.base.Links(data=value)

    def _normalize_adjust(self,
                          value: Optional[Union[
                              tmt.base._RawAdjustRule,
                              List[tmt.base._RawAdjustRule]]]
                          ) -> List[tmt.base._RawAdjustRule]:
        if value is None:
            return []
        return [value] if not isinstance(value, list) else value

    def _normalize_tier(self, value: Optional[Union[int, str]]) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    def _normalize_require(self, value: Optional[tmt.base._RawRequire]) -> List[tmt.base.Require]:
        return tmt.base.normalize_require(value)

    def _normalize_recommend(
            self,
            value: Optional[tmt.base._RawRequire]) -> List[tmt.base.Require]:
        return tmt.base.normalize_require(value)

    # ignore[override]: expected, we do want to accept more specific
    # type than the one declared in superclass.
    @classmethod
    def from_spec(  # type: ignore[override]
            cls: Type[T],
            raw_data: Dict[str, Any],
            logger: tmt.utils.Common
            ) -> T:
        """ Convert from a specification file or from a CLI option """

        data = cls(name=raw_data['name'], test=raw_data['test'])
        data._load_keys(raw_data, cls.__name__, logger)

        return data

    def to_spec(self) -> Dict[str, Any]:
        """ Convert to a form suitable for saving in a specification file """

        data = super().to_spec()
        data['link'] = self.link.to_spec() if self.link else None
        data['require'] = [require.to_spec() for require in self.require]
        data['recommend'] = [recommend.to_spec() for recommend in self.recommend]

        return data

    def to_serialized(self) -> Dict[str, Any]:
        """ Convert to a form suitable for saving in a file """

        data = super().to_serialized()

        # Using `to_spec()` on purpose: `Links` does not provide serialization
        # methods, because specification of links is already good enough. We
        # can use existing `to_spec()` method, and undo it with a simple
        # `Links(...)` call.
        data['link'] = self.link.to_spec() if self.link else None
        data['require'] = [require.to_spec() for require in self.require]
        data['recommend'] = [recommend.to_spec() for recommend in self.recommend]

        return data

    @classmethod
    def from_serialized(cls, serialized: Dict[str, Any]) -> 'TestDescription':
        """ Convert from a serialized form loaded from a file """

        obj = super().from_serialized(serialized)
        obj.link = tmt.base.Links(data=serialized['link'])
        obj.require = [
            tmt.base.RequireSimple.from_spec(require)
            if isinstance(require, str) else tmt.base.RequireFmfId.from_spec(require)
            for require in serialized['require']
            ]
        obj.recommend = [
            tmt.base.RequireSimple.from_spec(recommend)
            if isinstance(recommend, str) else tmt.base.RequireFmfId.from_spec(recommend)
            for recommend in serialized['recommend']
            ]

        return obj


@dataclasses.dataclass
class DiscoverShellData(tmt.steps.discover.DiscoverStepData):
    tests: List[TestDescription] = dataclasses.field(default_factory=list)

    url: Optional[str] = None
    ref: Optional[str] = None

    def _normalize_tests(self, value: List[Dict[str, Any]]
                         ) -> List[TestDescription]:
        return [TestDescription.from_spec(raw_datum, tmt.utils.Common()) for raw_datum in value]

    def to_serialized(self) -> Dict[str, Any]:
        """ Convert to a form suitable for saving in a file """

        serialized = super().to_serialized()

        serialized['tests'] = [test.to_serialized() for test in self.tests]

        return serialized

    @classmethod
    def from_serialized(cls, serialized: Dict[str, Any]) -> 'DiscoverShellData':
        """ Convert from a serialized form loaded from a file """

        obj = super().from_serialized(serialized)

        obj.tests = [TestDescription.from_serialized(
            serialized_test) for serialized_test in serialized['tests']]

        return obj


@tmt.steps.provides_method('shell')
class DiscoverShell(tmt.steps.discover.DiscoverPlugin):
    """
    Use provided list of shell script tests

    List of test cases to be executed can be defined manually directly
    in the plan as a list of dictionaries containing test name, actual
    test script and optionally a path to the test. Example config:

    discover:
        how: shell
        tests:
        - name: /help/main
          test: tmt --help
        - name: /help/test
          test: tmt test --help
        - name: /help/smoke
          test: ./smoke.sh
          path: /tests/shell

    For DistGit repo one can extract source tarball and use its code.
    It is extracted to TMT_SOURCE_DIR however no patches are applied
    (only source tarball is extracted).

    discover:
        how: shell
        dist-git-source: true
        tests:
        - name: /upstream
          test: cd $TMT_SOURCE_DIR/*/tests && make test

    To clone a remote repository and use it as a source specify `url`.
    It accepts also `ref` to checkout provided reference. Dynamic
    reference feature is supported as well.

    discover:
        how: shell
        url: https://github.com/teemtee/tmt.git
        ref: "1.18.0"
        tests:
        - name: first test
          test: ./script-from-the-repo.sh
    """

    _data_class = DiscoverShellData

    _tests: List[tmt.base.Test] = []

    def show(self, keys: Optional[List[str]] = None) -> None:
        """ Show config details """
        super().show([])
        # FIXME: cast() - typeless "dispatcher" method
        tests = cast(List[TestDescription], self.get('tests'))
        if tests:
            test_names = [test.name for test in tests]
            click.echo(tmt.utils.format('tests', test_names))

    def fetch_remote_repository(
            self, url: Optional[str], ref: Optional[str], testdir: str) -> None:
        """ Fetch remote git repo from given url to testdir """
        # Nothing to do if no url provided
        if not url:
            return

        # Clone first - it might clone dist git
        self.info('url', url, 'green')
        tmt.utils.git_clone(
            url=url,
            destination=testdir,
            common=self,
            env={"GIT_ASKPASS": "echo"},
            shallow=ref is None)

        # Resolve possible dynamic references
        try:
            ref = tmt.base.resolve_dynamic_ref(
                workdir=testdir,
                ref=ref,
                plan=self.step.plan,
                common=self)
        except tmt.utils.FileError as error:
            raise tmt.utils.DiscoverError(str(error))

        # Checkout revision if requested
        if ref:
            self.info('ref', ref, 'green')
            self.debug(f"Checkout ref '{ref}'.")
            self.run(['git', 'checkout', '-f', str(ref)], cwd=testdir)

        # Remove .git so that it's not copied to the SUT
        shutil.rmtree(os.path.join(testdir, '.git'))

    def go(self) -> None:
        """ Discover available tests """
        super(DiscoverShell, self).go()
        tests = fmf.Tree(dict(summary='tests'))

        assert self.workdir is not None
        testdir = os.path.join(self.workdir, "tests")

        # Fetch remote repository
        url = self.get('url', None)
        ref = self.get('ref', None)
        self.fetch_remote_repository(url, ref, testdir)

        # dist-git related
        sourcedir = os.path.join(self.workdir, 'source')
        dist_git_source = self.get('dist-git-source', False)

        # Check and process each defined shell test
        # FIXME: cast() - https://github.com/teemtee/tmt/issues/1540
        for data in cast(DiscoverShellData, self.data).tests:
            # Create data copy (we want to keep original data for save()
            data = copy.deepcopy(data)
            # Extract name, make sure it is present
            # TODO: can this ever happen? With annotations, `name: str` and `test: str`, nothing
            # should ever assign `None` there and pass the test.
            if not data.name:
                raise tmt.utils.SpecificationError(
                    f"Missing test name in '{self.step.plan.name}'.")
            # Make sure that the test script is defined
            if not data.test:
                raise tmt.utils.SpecificationError(
                    f"Missing test script in '{self.step.plan.name}'.")
            # Prepare path to the test working directory (tree root by default)
            data.path = f"/tests{data.path}" if data.path else '/tests'
            # Apply default test duration unless provided
            if not data.duration:
                data.duration = tmt.base.DEFAULT_TEST_DURATION_L2
            # Add source dir path variable
            if dist_git_source:
                data.environment['TMT_SOURCE_DIR'] = sourcedir

            # Create a simple fmf node, with correct name. Emit only keys and values
            # that are no longer default. Do not add `name` itself into the node,
            # it's not a supported test key, and it's given to the node itself anyway.
            # Note the exception for `duration` key - it's expected in the output
            # even if it still has its default value.
            test_fmf_keys: Dict[str, Any] = {
                key: value
                for key, value in data.to_spec().items()
                if key != 'name' and (key == 'duration' or value != data.default(key))
                }
            tests.child(data.name, test_fmf_keys)

        # Symlink tests directory to the plan work tree
        # (unless remote repository is provided using 'url')
        if not url:
            relative_path = os.path.relpath(self.step.plan.worktree, self.workdir)
            os.symlink(relative_path, testdir)

        if dist_git_source:
            assert self.step.plan.my_run is not None  # narrow type
            assert self.step.plan.my_run.tree is not None  # narrow type
            assert self.step.plan.my_run.tree.root is not None  # narrow type
            try:
                run_result = self.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=self.step.plan.my_run.tree.root,
                    dry=True)[0]
                assert run_result is not None
                git_root = run_result.strip('\n')
            except tmt.utils.RunError:
                assert self.step.plan.my_run is not None  # narrow type
                assert self.step.plan.my_run.tree is not None  # narrow type
                raise tmt.utils.DiscoverError(
                    f"Directory '{self.step.plan.my_run.tree.root}' "
                    f"is not a git repository.")
            try:
                self.extract_distgit_source(
                    git_root, sourcedir, self.get('dist-git-type'))
            except Exception as error:
                raise tmt.utils.DiscoverError(
                    "Failed to process 'dist-git-source'.") from error

        # Use a tmt.Tree to apply possible command line filters
        self._tests = tmt.Tree(tree=tests).tests(conditions=["manual is False"])

    def tests(self) -> List[tmt.base.Test]:
        return self._tests
