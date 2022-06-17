# coding: utf-8

import datetime
import os
import re
import time
import unittest
import unittest.mock

import pytest

import tmt
from tmt.utils import (Common, GeneralError, StructuredField,
                       StructuredFieldError, WaitingIncomplete,
                       WaitingTimedOutError, duration_to_seconds, listify,
                       public_git_url, validate_git_status, wait)

run = Common().run


@pytest.fixture
def local_git_repo(tmpdir):
    origin = tmpdir.join('origin')
    os.makedirs(origin)

    run('git init'.split(), cwd=origin)
    run(
        'git config --local user.email lzachar@redhat.com'.split(),
        cwd=origin)
    run(
        'git config --local user.name LZachar'.split(),
        cwd=origin)
    # We need to be able to push, --bare repo is another option here however
    # that would require to add separate fixture for bare repo (unusable for
    # local changes)
    run(
        'git config --local receive.denyCurrentBranch ignore'.split(),
        cwd=origin)
    origin.join('README').write('something to have in the repo')
    run('git add -A'.split(), cwd=origin)
    run(
        'git commit -m initial_commit'.split(),
        cwd=origin)
    return origin


@pytest.fixture
def origin_and_local_git_repo(local_git_repo):
    top_dir = local_git_repo.dirpath()
    fork_dir = top_dir.join('fork')
    run(
        f'git clone {local_git_repo} {fork_dir}'.split(),
        cwd=top_dir)
    run(
        'git config --local user.email lzachar@redhat.com'.split(),
        cwd=fork_dir)
    run(
        'git config --local user.name LZachar'.split(),
        cwd=fork_dir)
    return local_git_repo, fork_dir


def test_public_git_url():
    """ Verify url conversion """
    examples = [
        {
            'original': 'git@github.com:teemtee/tmt.git',
            'expected': 'https://github.com/teemtee/tmt.git',
            }, {
            'original': 'ssh://psplicha@pkgs.devel.redhat.com/tests/bash',
            'expected': 'git://pkgs.devel.redhat.com/tests/bash',
            }, {
            'original': 'git+ssh://psplicha@pkgs.devel.redhat.com/tests/bash',
            'expected': 'git://pkgs.devel.redhat.com/tests/bash',
            }, {
            'original': 'ssh://pkgs.devel.redhat.com/tests/bash',
            'expected': 'git://pkgs.devel.redhat.com/tests/bash',
            }, {
            'original': 'git+ssh://psss@pkgs.fedoraproject.org/tests/shell',
            'expected': 'https://pkgs.fedoraproject.org/tests/shell',
            }, {
            'original': 'ssh://psss@pkgs.fedoraproject.org/tests/shell',
            'expected': 'https://pkgs.fedoraproject.org/tests/shell',
            }, {
            'original': 'ssh://git@pagure.io/fedora-ci/metadata.git',
            'expected': 'https://pagure.io/fedora-ci/metadata.git',
            },
        ]
    for example in examples:
        assert public_git_url(example['original']) == example['expected']


def test_listify():
    """ Check listify functionality """
    assert listify(['abc']) == ['abc']
    assert listify('abc') == ['abc']
    assert listify('a b c') == ['a b c']
    assert listify('a b c', split=True) == ['a', 'b', 'c']
    assert listify(dict(a=1, b=2)) == dict(a=[1], b=[2])
    assert listify(dict(a=1, b=2), keys=['a']) == dict(a=[1], b=2)


def test_config():
    """ Config smoke test """
    run = '/var/tmp/tmt/test'
    config1 = tmt.utils.Config()
    config1.last_run(run)
    config2 = tmt.utils.Config()
    assert config2.last_run() == run


def test_duration_to_seconds():
    """ Check conversion from sleep time format to seconds """
    assert duration_to_seconds(5) == 5
    assert duration_to_seconds('5') == 5
    assert duration_to_seconds('5s') == 5
    assert duration_to_seconds('5m') == 300
    assert duration_to_seconds('5h') == 18000
    assert duration_to_seconds('5d') == 432000
    with pytest.raises(tmt.utils.SpecificationError):
        duration_to_seconds('bad')


class test_structured_field(unittest.TestCase):
    """ Self Test """

    def setUp(self):
        self.header = "This is a header.\n"
        self.footer = "This is a footer.\n"
        self.start = (
            "[structured-field-start]\n"
            "This is StructuredField version 1. "
            "Please, edit with care.\n")
        self.end = "[structured-field-end]\n"
        self.zeroend = "[end]\n"
        self.one = "[one]\n1\n"
        self.two = "[two]\n2\n"
        self.three = "[three]\n3\n"
        self.sections = "\n".join([self.one, self.two, self.three])

    def test_everything(self):
        """ Everything """
        # Version 0
        text0 = "\n".join([
                self.header,
                self.sections, self.zeroend,
                self.footer])
        inited0 = StructuredField(text0, version=0)
        loaded0 = StructuredField()
        loaded0.load(text0, version=0)
        self.assertEqual(inited0.save(), text0)
        self.assertEqual(loaded0.save(), text0)
        # Version 1
        text1 = "\n".join([
                self.header,
                self.start, self.sections, self.end,
                self.footer])
        inited1 = StructuredField(text1)
        loaded1 = StructuredField()
        loaded1.load(text1)
        self.assertEqual(inited1.save(), text1)
        self.assertEqual(loaded1.save(), text1)
        # Common checks
        for field in [inited0, loaded0, inited1, loaded1]:
            self.assertEqual(field.header(), self.header)
            self.assertEqual(field.footer(), self.footer)
            self.assertEqual(field.sections(), ["one", "two", "three"])
            self.assertEqual(field.get("one"), "1\n")
            self.assertEqual(field.get("two"), "2\n")
            self.assertEqual(field.get("three"), "3\n")

    def test_no_header(self):
        """ No header """
        # Version 0
        text0 = "\n".join([self.sections, self.zeroend, self.footer])
        field0 = StructuredField(text0, version=0)
        self.assertEqual(field0.save(), text0)
        # Version 1
        text1 = "\n".join(
                [self.start, self.sections, self.end, self.footer])
        field1 = StructuredField(text1)
        self.assertEqual(field1.save(), text1)
        # Common checks
        for field in [field0, field1]:
            self.assertEqual(field.header(), "")
            self.assertEqual(field.footer(), self.footer)
            self.assertEqual(field.get("one"), "1\n")
            self.assertEqual(field.get("two"), "2\n")
            self.assertEqual(field.get("three"), "3\n")

    def test_no_footer(self):
        """ No footer """
        # Version 0
        text0 = "\n".join([self.header, self.sections, self.zeroend])
        field0 = StructuredField(text0, version=0)
        self.assertEqual(field0.save(), text0)
        # Version 1
        text1 = "\n".join(
                [self.header, self.start, self.sections, self.end])
        field1 = StructuredField(text1)
        self.assertEqual(field1.save(), text1)
        # Common checks
        for field in [field0, field1]:
            self.assertEqual(field.header(), self.header)
            self.assertEqual(field.footer(), "")
            self.assertEqual(field.get("one"), "1\n")
            self.assertEqual(field.get("two"), "2\n")
            self.assertEqual(field.get("three"), "3\n")

    def test_just_sections(self):
        """ Just sections """
        # Version 0
        text0 = "\n".join([self.sections, self.zeroend])
        field0 = StructuredField(text0, version=0)
        self.assertEqual(field0.save(), text0)
        # Version 1
        text1 = "\n".join([self.start, self.sections, self.end])
        field1 = StructuredField(text1)
        self.assertEqual(field1.save(), text1)
        # Common checks
        for field in [field0, field1]:
            self.assertEqual(field.header(), "")
            self.assertEqual(field.footer(), "")
            self.assertEqual(field.get("one"), "1\n")
            self.assertEqual(field.get("two"), "2\n")
            self.assertEqual(field.get("three"), "3\n")

    def test_plain_text(self):
        """ Plain text """
        text = "Some plain text.\n"
        field0 = StructuredField(text, version=0)
        field1 = StructuredField(text)
        for field in [field0, field1]:
            self.assertEqual(field.header(), text)
            self.assertEqual(field.footer(), "")
            self.assertEqual(field.save(), text)
            self.assertEqual(list(field), [])
            self.assertEqual(bool(field), False)

    def test_missing_end_tag(self):
        """ Missing end tag """
        text = "\n".join([self.header, self.sections, self.footer])
        self.assertRaises(StructuredFieldError, StructuredField, text, 0)

    def test_broken_field(self):
        """ Broken field"""
        text = "[structured-field-start]"
        self.assertRaises(StructuredFieldError, StructuredField, text)

    def test_set_content(self):
        """ Set section content """
        field0 = StructuredField(version=0)
        field1 = StructuredField()
        for field in [field0, field1]:
            field.set("one", "1")
            self.assertEqual(field.get("one"), "1\n")
            field.set("two", "2")
            self.assertEqual(field.get("two"), "2\n")
            field.set("three", "3")
            self.assertEqual(field.get("three"), "3\n")
        self.assertEqual(field0.save(), "\n".join(
            [self.sections, self.zeroend]))
        self.assertEqual(field1.save(), "\n".join(
            [self.start, self.sections, self.end]))

    def test_remove_section(self):
        """ Remove section """
        field0 = StructuredField(
            "\n".join([self.sections, self.zeroend]), version=0)
        field1 = StructuredField(
            "\n".join([self.start, self.sections, self.end]))
        for field in [field0, field1]:
            field.remove("one")
            field.remove("two")
        self.assertEqual(
            field0.save(), "\n".join([self.three, self.zeroend]))
        self.assertEqual(
            field1.save(), "\n".join([self.start, self.three, self.end]))

    def test_section_tag_escaping(self):
        """ Section tag escaping """
        field = StructuredField()
        field.set("section", "\n[content]\n")
        reloaded = StructuredField(field.save())
        self.assertTrue("section" in reloaded)
        self.assertTrue("content" not in reloaded)
        self.assertEqual(reloaded.get("section"), "\n[content]\n")

    def test_nesting(self):
        """ Nesting """
        # Prepare structure parent -> child -> grandchild
        grandchild = StructuredField()
        grandchild.set('name', "Grand Child\n")
        child = StructuredField()
        child.set('name', "Child Name\n")
        child.set("child", grandchild.save())
        parent = StructuredField()
        parent.set("name", "Parent Name\n")
        parent.set("child", child.save())
        # Reload back and check the names
        parent = StructuredField(parent.save())
        child = StructuredField(parent.get("child"))
        grandchild = StructuredField(child.get("child"))
        self.assertEqual(parent.get("name"), "Parent Name\n")
        self.assertEqual(child.get("name"), "Child Name\n")
        self.assertEqual(grandchild.get("name"), "Grand Child\n")

    def test_section_tags_in_header(self):
        """ Section tags in header """
        field = StructuredField("\n".join(
            ["[something]", self.start, self.one, self.end]))
        self.assertTrue("something" not in field)
        self.assertTrue("one" in field)
        self.assertEqual(field.get("one"), "1\n")

    def test_empty_section(self):
        """ Empty section """
        field = StructuredField()
        field.set("section", "")
        reloaded = StructuredField(field.save())
        self.assertEqual(reloaded.get("section"), "")

    def test_section_item_get(self):
        """ Get section item """
        text = "\n".join([self.start, "[section]\nx = 3\n", self.end])
        field = StructuredField(text)
        self.assertEqual(field.get("section", "x"), "3")

    def test_section_item_set(self):
        """ Set section item """
        text = "\n".join([self.start, "[section]\nx = 3\n", self.end])
        field = StructuredField()
        field.set("section", "3", "x")
        self.assertEqual(field.save(), text)

    def test_section_item_remove(self):
        """ Remove section item """
        text = "\n".join(
            [self.start, "[section]\nx = 3\ny = 7\n", self.end])
        field = StructuredField(text)
        field.remove("section", "x")
        self.assertEqual(field.save(), "\n".join(
            [self.start, "[section]\ny = 7\n", self.end]))

    def test_unicode_header(self):
        """ Unicode text in header """
        text = u"Už abychom měli unicode jako defaultní kódování!"
        field = StructuredField(text)
        field.set("section", "content")
        self.assertTrue(text in field.save())

    def test_unicode_section_content(self):
        """ Unicode in section content """
        chars = u"ěščřžýáíéů"
        text = "\n".join([self.start, "[section]", chars, self.end])
        field = StructuredField(text)
        self.assertEqual(field.get("section").strip(), chars)

    def test_unicode_section_name(self):
        """ Unicode in section name """
        chars = u"ěščřžýáíéů"
        text = "\n".join([self.start, u"[{0}]\nx".format(chars), self.end])
        field = StructuredField(text)
        self.assertEqual(field.get(chars).strip(), "x")

    def test_header_footer_modify(self):
        """ Modify header & footer """
        original = StructuredField()
        original.set("field", "field-content")
        original.header("header-content\n")
        original.footer("footer-content\n")
        copy = StructuredField(original.save())
        self.assertEqual(copy.header(), "header-content\n")
        self.assertEqual(copy.footer(), "footer-content\n")

    def test_trailing_whitespace(self):
        """ Trailing whitespace """
        original = StructuredField()
        original.set("name", "value")
        # Test with both space and tab appended after the section tag
        for char in [" ", "\t"]:
            spaced = re.sub(r"\]\n", "]{0}\n".format(char), original.save())
            copy = StructuredField(spaced)
            self.assertEqual(original.get("name"), copy.get("name"))

    def test_carriage_returns(self):
        """ Carriage returns """
        text1 = "\n".join([self.start, self.sections, self.end])
        text2 = re.sub(r"\n", "\r\n", text1)
        field1 = StructuredField(text1)
        field2 = StructuredField(text2)
        self.assertEqual(field1.save(), field2.save())

    def test_multiple_values(self):
        """ Multiple values """
        # Reading multiple values
        section = "[section]\nkey=val1 # comment\nkey = val2\n key = val3 "
        text = "\n".join([self.start, section, self.end])
        field = StructuredField(text, multi=True)
        self.assertEqual(
            field.get("section", "key"), ["val1", "val2", "val3"])
        # Writing multiple values
        values = ['1', '2', '3']
        field = StructuredField(multi=True)
        field.set("section", values, "key")
        self.assertEqual(field.get("section", "key"), values)
        self.assertTrue("key = 1\nkey = 2\nkey = 3" in field.save())
        # Remove multiple values
        field.remove("section", "key")
        self.assertTrue("key = 1\nkey = 2\nkey = 3" not in field.save())
        self.assertRaises(
            StructuredFieldError, field.get, "section", "key")


class Run(unittest.TestCase):

    def test_interactive_not_joined(self):
        stdout, stderr = Common()._run(
            "echo abc; echo def >2", shell=True, interactive=True, cwd=".", env={}, log=None)
        self.assertEqual(stdout, None)
        self.assertEqual(stderr, None)

    def test_interactive_joined(self):
        stdout, _ = Common()._run(
            "echo abc; echo def >2",
            shell=True,
            interactive=True,
            cwd=".",
            env={},
            join=True,
            log=None)
        self.assertEqual(stdout, None)

    def test_not_joined_stdout(self):
        stdout, _ = Common()._run("ls /", shell=True, cwd=".", env={}, log=None)
        self.assertIn("sbin", stdout)

    def test_not_joined_stderr(self):
        _, stderr = Common()._run("ls non_existing || true", shell=True, cwd=".", env={}, log=None)
        self.assertIn("ls: cannot access", stderr)

    def test_joined(self):
        stdout, _ = Common()._run(
            "ls non_existing / || true",
            shell=True,
            cwd=".",
            env={},
            log=None,
            join=True)
        self.assertIn("ls: cannot access", stdout)
        self.assertIn("sbin", stdout)

    def test_big(self):
        stdout, _ = Common()._run(
            """for NUM in {1..100}; do LINE="$LINE n"; done; for NUM in {1..1000}; do echo $LINE; done""",  # noqa: E501
            shell=True,
            cwd=".",
            env={},
            log=None,
            join=True)
        self.assertIn("n n", stdout)
        self.assertEqual(len(stdout), 200000)


def test_get_distgit_handler():
    for wrong_remotes in [[], ["blah"]]:
        with pytest.raises(tmt.utils.GeneralError):
            tmt.utils.get_distgit_handler([])
    # Fedora detection
    returned_object = tmt.utils.get_distgit_handler("""
        remote.origin.url ssh://lzachar@pkgs.fedoraproject.org/rpms/tmt
        remote.lzachar.url ssh://lzachar@pkgs.fedoraproject.org/forks/lzachar/rpms/tmt.git
        """.split('\n'))
    assert isinstance(returned_object, tmt.utils.FedoraDistGit)
    # CentOS detection
    returned_object = tmt.utils.get_distgit_handler("""
        remote.origin.url git+ssh://git@gitlab.com/redhat/centos-stream/rpms/ruby.git
        """.split('\n'))
    assert isinstance(returned_object, tmt.utils.CentOSDistGit)


def test_FedoraDistGit(tmpdir):
    # Fake values, production hash is too long
    tmpdir.join('sources').write(
        'SHA512 (fn-1.tar.gz) = 09af\n')
    tmpdir.join('tmt.spec').write('')
    fedora_sources_obj = tmt.utils.FedoraDistGit()
    assert [("https://src.fedoraproject.org/repo/pkgs/rpms/tmt/fn-1.tar.gz/sha512/09af/fn-1.tar.gz",  # noqa: E501
            "fn-1.tar.gz")] == fedora_sources_obj.url_and_name(cwd=tmpdir)


class Test_validate_git_status:
    @pytest.mark.parametrize("use_path",
                             [False, True], ids=["without path", "with path"])
    def test_all_good(cls, origin_and_local_git_repo, use_path):
        # No need to modify origin, ignoring it
        mine = origin_and_local_git_repo[1]

        # In local repo:
        # Init tmt and add test
        if use_path:
            fmf_root = mine.join('fmf_root')
        else:
            fmf_root = mine
        tmt.Tree.init(str(fmf_root), None, None)
        fmf_root.join('main.fmf').write('test: echo')
        run(
            ['git', 'add', str(fmf_root), str(fmf_root.join('main.fmf'))],
            cwd=mine)
        run(
            'git commit -m add_test'.split(),
            cwd=mine)
        run(
            'git push'.split(),
            cwd=mine)
        test = tmt.Tree(str(fmf_root)).tests()[0]
        validation = validate_git_status(test)
        assert validation == (True, '')

    def test_no_remote(cls, local_git_repo):
        tmpdir = local_git_repo
        tmt.Tree.init(str(tmpdir), None, None)
        tmpdir.join('main.fmf').write('test: echo')
        run(
            'git add main.fmf .fmf/version'.split(),
            cwd=tmpdir)
        run(
            'git commit -m initial_commit'.split(),
            cwd=tmpdir)

        test = tmt.Tree(str(tmpdir)).tests()[0]
        val, msg = validate_git_status(test)
        assert not val
        assert "Failed to get remote branch" in msg

    def test_untracked_fmf_root(cls, local_git_repo):
        # local repo is enough since this can't get passed 'is pushed' check
        tmt.Tree.init(str(local_git_repo), None, None)
        local_git_repo.join('main.fmf').write('test: echo')
        run(
            'git add main.fmf'.split(),
            cwd=local_git_repo)
        run(
            'git commit -m missing_fmf_root'.split(),
            cwd=local_git_repo)

        test = tmt.Tree(str(local_git_repo)).tests()[0]
        validate = validate_git_status(test)
        assert validate == (False, 'Uncommitted changes in .fmf/version')

    def test_untracked_sources(cls, local_git_repo):
        tmt.Tree.init(str(local_git_repo), None, None)
        local_git_repo.join('main.fmf').write('test: echo')
        local_git_repo.join('test.fmf').write('tag: []')
        run(
            'git add .fmf/version test.fmf'.split(),
            cwd=local_git_repo)
        run(
            'git commit -m main.fmf'.split(),
            cwd=local_git_repo)

        test = tmt.Tree(str(local_git_repo)).tests()[0]
        validate = validate_git_status(test)
        assert validate == (False, 'Uncommitted changes in main.fmf')

    @pytest.mark.parametrize("use_path",
                             [False, True], ids=["without path", "with path"])
    def test_local_changes(cls, origin_and_local_git_repo, use_path):
        origin, mine = origin_and_local_git_repo

        if use_path:
            fmf_root = origin.join('fmf_root')
        else:
            fmf_root = origin
        tmt.Tree.init(str(fmf_root), None, None)
        fmf_root.join('main.fmf').write('test: echo')
        run('git add -A'.split(), cwd=origin)
        run(
            'git commit -m added_test'.split(),
            cwd=origin)

        # Pull changes from previous line
        run('git pull'.split(),
            cwd=mine)

        mine_fmf_root = mine
        if use_path:
            mine_fmf_root = mine.join('fmf_root')
        mine_fmf_root.join('main.fmf').write('test: echo ahoy')

        # Change README but since it is not part of metadata we do not check it
        mine.join("README").write('changed')

        test = tmt.Tree(str(mine_fmf_root)).tests()[0]
        validation_result = validate_git_status(test)

        assert validation_result == (
            False, "Uncommitted changes in " + ('fmf_root/' if use_path else '') + "main.fmf")

    def test_not_pushed(cls, origin_and_local_git_repo):
        # No need for original repo (it is required just to have remote in
        # local clone)
        mine = origin_and_local_git_repo[1]
        fmf_root = mine

        tmt.Tree.init(str(fmf_root), None, None)

        fmf_root.join('main.fmf').write('test: echo')
        run(
            'git add main.fmf .fmf/version'.split(),
            cwd=fmf_root)
        run(
            'git commit -m changes'.split(),
            cwd=mine)

        test = tmt.Tree(str(fmf_root)).tests()[0]
        validation_result = validate_git_status(test)

        assert validation_result == (
            False, 'Not pushed changes in .fmf/version main.fmf')


#
# tmt.utils.wait() & waiting for things to happen
#
def test_wait_bad_tick():
    """
    :py:func:`wait` shall raise an exception when invalid ``tick`` is given.
    """

    with pytest.raises(GeneralError, match='Tick must be a positive integer'):
        wait(Common(), lambda: False, datetime.timedelta(seconds=1), tick=-1)


def test_wait_deadline_already_passed():
    """
    :py:func:`wait` shall not call ``check`` if the given timeout leads to
    already expired deadline.
    """

    ticks = []

    with pytest.raises(WaitingTimedOutError):
        wait(Common(), lambda: ticks.append(1), datetime.timedelta(seconds=-86400))

    # our callback should not have been called at all
    assert not ticks


def test_wait():
    """
    :py:func:`wait` shall call ``check`` multiple times until ``check`` returns
    successfully.
    """

    # Every tick of wait()'s loop, pop one item. Once we get to the end,
    # consider the condition to be fulfilled.
    ticks = list(range(1, 10))

    # Make sure check's return value is propagated correctly, make it unique.
    return_value = unittest.mock.MagicMock()

    def check():
        if not ticks:
            return return_value

        ticks.pop()

        raise WaitingIncomplete()

    # We want to reach end of our list, give enough time budget.
    r = wait(Common(), check, datetime.timedelta(seconds=3600), tick=0.01)

    assert r is return_value
    assert not ticks


def test_wait_timeout():
    """
    :py:func:`wait` shall call ``check`` multiple times until ``check`` running
    out of time.
    """

    check = unittest.mock.MagicMock(
        __name__='mock_check',
        side_effect=WaitingIncomplete)

    # We want to reach end of time budget before reaching end of the list.
    with pytest.raises(WaitingTimedOutError):
        wait(Common(), check, datetime.timedelta(seconds=1), tick=0.1)

    # Verify our callback has been called. It's hard to predict how often it
    # should have been called, hopefully 10 times (1 / 0.1), but timing things
    # in test is prone to errors, process may get suspended, delayed, whatever,
    # and we'd end up with 9 calls and a failed test. In any case, it must be
    # 10 or less, because it's not possible to fit 11 calls into 1 second.
    check.assert_called()
    assert len(check.mock_calls) <= 10


def test_wait_success_but_too_late():
    """
    :py:func:`wait` shall report failure even when ``check`` succeeds but runs
    out of time.
    """

    def check():
        time.sleep(5)

    with pytest.raises(WaitingTimedOutError):
        wait(Common(), check, datetime.timedelta(seconds=1))
