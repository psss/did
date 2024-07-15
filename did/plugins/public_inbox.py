# coding: utf-8
"""
Public-Inbox stats about mailing lists threads

Config example::

    [inbox]
    type = public-inbox
    url = https://lore.kernel.org
"""

import copy
import datetime
import email.utils
import gzip
import mailbox
import tempfile
import typing
import urllib.parse

import requests

from did.base import Config, Date, ReportError, User
from did.stats import Stats, StatsGroup
from did.utils import item, log


class Message(object):
    def __init__(self, msg: mailbox.mboxMessage) -> None:
        self.msg = msg

    def __msg_id(self, keyid: str) -> typing.Optional[str]:
        msgid = self.msg[keyid]
        if msgid is None:
            log.debug("Missing header %s" % keyid)
            return None

        return msgid.lstrip("<").rstrip(">")

    def id(self) -> typing.Optional[str]:
        return self.__msg_id("Message-Id")

    def parent_id(self) -> typing.Optional[str]:
        return self.__msg_id("In-Reply-To")

    def subject(self) -> str:
        subject = self.msg["Subject"]

        subject = " ".join(subject.splitlines())
        subject = " ".join(subject.split())

        return subject

    def date(self) -> datetime.datetime:
        return email.utils.parsedate_to_datetime(self.msg["Date"])

    def is_thread_root(self) -> bool:
        return self.parent_id() is None

    def is_from_user(self, user: str) -> bool:
        msg_from = email.utils.parseaddr(self.msg["From"])[1]

        return email.utils.parseaddr(user)[1] == msg_from

    def is_between_dates(self, since: Date, until: Date) -> bool:
        msg_date = self.date().date()

        return msg_date >= since.date and msg_date <= until.date


def _unique_messages(mbox: mailbox.mbox) -> typing.Iterable[Message]:
    msgs = dict()
    for msg in mbox.values():
        msg = Message(msg)
        id = msg.id()

        if id not in msgs:
            msgs[id] = msg
            yield msg


class PublicInbox(object):
    def __init__(self, parent, user: User, url: str) -> None:
        self.parent = parent
        self.threads_cache = dict()
        self.messages_cache = dict()
        self.url = url
        self.user = user

    def __get_url(self, path: str) -> str:
        return urllib.parse.urljoin(self.url, path)

    def _get_message_url(self, msg: Message) -> str:
        return self.__get_url("/r/%s/" % msg.id())

    def _print_msg(self, options, msg: Message) -> None:
        if options.format == 'markdown':
            item("[{0}]({1})".format(msg.subject(), self._get_message_url(msg)),
                 level=1, options=options)

        else:
            item(msg.subject(), level=1, options=options)

            if options.verbose:
                opt = copy.deepcopy(options)
                opt.width = 0
                item(self._get_message_url(msg), level=2, options=opt)

    def __get_mbox_from_content(self, content: bytes) -> mailbox.mbox:
        content = gzip.decompress(content)

        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(content)
            tmp.seek(0)

            return mailbox.mbox(tmp.name)

    def __get_msgs_from_mbox(self, mbox: mailbox.mbox) -> list[Message]:
        msgs = list()

        for msg in _unique_messages(mbox):
            msg_id = msg.id()

            log.debug("Found message %s." % msg_id)
            msgs.append(msg)

            if msg_id not in self.messages_cache:
                log.debug("Message %s is new, adding to the cache." % msg_id)
                self.messages_cache[msg_id] = msg

        return msgs

    def __fetch_thread_root(self, msg: Message) -> typing.Optional[Message]:
        msg_id = msg.id()
        url = self.__get_url("/all/%s/t.mbox.gz" % msg_id)

        log.debug("Fetching message %s thread (%s)" % (msg_id, url))
        resp = requests.get(url)
        mbox = self.__get_mbox_from_content(resp.content)
        for msg in self.__get_msgs_from_mbox(mbox):
            if msg.is_thread_root():
                log.debug("Found message %s thread root: %s." % (msg_id, msg.id()))
                return msg

        log.warn("Couldn't find message root")
        return None

    def __get_thread_root(self, msg: Message) -> Message:
        log.debug("Looking for thread root of message %s" % msg.id())
        if msg.is_thread_root():
            log.debug("Message is thread root already. Returning.")
            return msg

        parent_id = msg.parent_id()
        if parent_id not in self.messages_cache:
            root = self.__fetch_thread_root(msg)
            if root is None:
                log.debug("Can't retrieve the thread root, returning.")
                return msg

            log.debug("Found root message %s for message %s" % (root.id(), msg.id()))
            return root

        while True:
            log.debug("Parent is %s" % parent_id)
            assert parent_id in self.messages_cache
            parent = self.messages_cache[parent_id]
            if parent.is_thread_root():
                log.debug("Parent is the thread root, returning.")
                return parent

            parent_id = parent.parent_id()
            if parent_id not in self.messages_cache:
                root = self.__fetch_thread_root(parent)
                if root is None:
                    log.debug("Can't retrieve the message parent, returning.")
                    return parent

                log.debug(
                    "Found root message %s for message %s" %
                    (root.id(), msg.id()))
                return root

    def __fetch_all_threads(self, since: Date, until: Date) -> list[Message]:
        since_str = since.date.isoformat()
        until_str = until.date.isoformat()

        log.info("Fetching all mails on server %s from %s between %s and %s" %
                 (self.url, self.user, since_str, until_str))
        resp = requests.post(
            self.__get_url("/all/"),
            headers={"Content-Length": "0"},
            params={
                "q": "(f:%s AND d:%s..%s)"
                % (self.user.email, since_str, until_str),
                "x": "m",
                },
            )

        if not resp.ok:
            return []

        mbox = self.__get_mbox_from_content(resp.content)
        return self.__get_msgs_from_mbox(mbox)

    def get_all_threads(self, since: Date, until: Date):
        if (since, until) not in self.threads_cache:
            self.threads_cache[(since, until)] = self.__fetch_all_threads(since, until)

        assert (since, until) in self.threads_cache

        found = list()
        for msg in self.threads_cache[(since, until)]:
            msg_id = msg.id()
            if msg_id in found:
                continue

            if not msg.is_thread_root():
                root = self.__get_thread_root(msg)
                root_id = root.id()
                if root_id in found:
                    log.debug("Root message already encountered... Skip.")
                    continue

                found.append(root_id)
                yield root
            else:
                found.append(msg_id)
                yield msg


class ThreadsStarted(Stats):
    """ Mail threads started """

    def fetch(self):
        log.info(
            "Searching for new threads on {0} started by {1}".format(
                self.parent.url,
                self.user,
                )
            )

        self.stats = [
            msg
            for msg in self.parent.public_inbox.get_all_threads(
                self.options.since, self.options.until)
            if msg.is_from_user(self.user.email)
            and msg.is_between_dates(self.options.since, self.options.until)
            ]

    def show(self):
        if not self._error and not self.stats:
            return

        self.header()
        for msg in self.stats:
            self.parent.public_inbox._print_msg(self.options, msg)


class ThreadsInvolved(Stats):
    """ Mail threads involved in """

    def fetch(self):
        log.info(
            "Searching for mail threads on {0} where {1} was involved".format(
                self.parent.url,
                self.user,
                )
            )

        self.stats = [
            msg
            for msg in self.parent.public_inbox.get_all_threads(
                self.options.since, self.options.until)
            if not msg.is_from_user(self.user.email)
            or not msg.is_between_dates(self.options.since, self.options.until)
            ]

    def show(self):
        if not self._error and not self.stats:
            return

        self.header()
        for msg in self.stats:
            self.parent.public_inbox._print_msg(self.options, msg)


class PublicInboxStats(StatsGroup):
    """ Public-Inbox Mailing List Archive """

    order = 750

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)

        config = dict(Config().section(option))
        try:
            self.url = config["url"]
        except KeyError:
            raise ReportError("No url in the [{0}] section.".format(option))

        self.public_inbox = PublicInbox(self.parent, self.user, self.url)
        self.stats = [
            ThreadsStarted(option=option + "-started", parent=self),
            ThreadsInvolved(option=option + "-involved", parent=self),
            ]
