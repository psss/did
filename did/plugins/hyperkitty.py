"""
Hyperkitty stats about mailing lists threads

Config example::

    [centos-virt-list]
    type = hyperkitty
    url = https://lists.centos.org/hyperkitty/list/virt@lists.centos.org

It's also possible to set a timeout, if not specified it defaults to
60 seconds.

    timeout = 10

"""  # noqa: W505

import copy
import datetime
import email.utils
import gzip
import mailbox
import tempfile
import typing
import urllib.parse
from base64 import b32encode
from hashlib import sha1

import requests

from did.base import Config, Date, ReportError, User
from did.stats import Stats, StatsGroup
from did.utils import item, log

# Default number of seconds waiting on inbox before giving up
TIMEOUT = 60


class Message():
    def __init__(self, msg: mailbox.mboxMessage) -> None:
        self.msg = msg

    def __msg_id(self, keyid: str) -> str:
        msgid = self.msg[keyid]
        if msgid is None:
            return None

        return msgid.lstrip("<").rstrip(">")

    def id(self) -> str:
        return self.__msg_id("Message-Id")

    def id_hash(self) -> str:
        return b32encode(sha1(self.id().encode()).digest()).decode()

    def parent_id(self) -> str:
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

    def mail_from(self) -> str:
        return email.utils.parseaddr(self.msg["From"])[1]

    def is_from_user(self, user: str) -> bool:
        original = email.utils.parseaddr(user)[1]
        masked = original.replace("@", " at ")
        return self.mail_from() in (original, masked)

    def is_between_dates(self, since: Date, until: Date) -> bool:
        msg_date = self.date().date()

        return msg_date >= since.date and msg_date <= until.date


def _unique_messages(mbox: mailbox.mbox) -> typing.Iterable[Message]:
    msgs = dict()
    for msg in mbox.values():
        msg = Message(msg)
        msg_id = msg.id()

        if msg_id not in msgs:
            msgs[msg_id] = msg
            yield msg


class Hyperkitty():
    def __init__(self, parent, user: User, url: str, timeout: int = TIMEOUT) -> None:
        self.parent = parent
        self.threads_cache = dict()
        self.messages_cache = dict()
        self.url = url
        self.user = user
        self.timeout = timeout

    def __get_url(self, path: str) -> str:
        return urllib.parse.urljoin(self.url, path)

    def _get_message_url(self, msg: Message) -> str:
        return self.__get_url(f"message/{msg.id_hash()}/")

    def print_msg(self, options, msg: Message) -> None:
        if options.format == 'markdown':
            item(f"[{msg.subject()}]({self._get_message_url(msg)})",
                 level=1,
                 options=options
                 )

        else:
            item(msg.subject(), level=1, options=options)

            if options.verbose:
                opt = copy.deepcopy(options)
                opt.width = 0
                item(self._get_message_url(msg), level=2, options=opt)

    def __get_mbox_from_content(self, content: bytes) -> mailbox.mbox:
        """
        :param content: a blob of data compressed with gzip algorithm
        :returns: a mailbox.mbox object built from the given content
        """
        content = gzip.decompress(content)

        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(content)
            tmp.seek(0)

            return mailbox.mbox(tmp.name)

    def __get_msgs_from_mbox(self, mbox: mailbox.mbox) -> list[Message]:
        """
        :param mbox: a mailbox object
        :returns: a list of messages
        """
        msgs = []

        for msg in _unique_messages(mbox):
            msg_id = msg.id()

            log.debug("Found message %s.", msg_id)
            msgs.append(msg)

            if msg_id not in self.messages_cache:
                log.debug("Message %s is new, adding to the cache.", msg_id)
                self.messages_cache[msg_id] = msg

        return msgs

    def __fetch_thread_root(self, initial_msg: Message) -> Message:
        """
        Given a message from a thread, thry to find the root message
        of the thread within the mbox.
        :param intial_msg: the message we want to process.
        :returns: the root message of the thread `initial_msg`
                  belongs to.
        """
        msg_id = initial_msg.id()
        msg_hash = initial_msg.id_hash()
        url = self.__get_url(f"export/thread.mbox.gz?thread={msg_hash}")
        log.debug("Fetching message %s thread (%s)", msg_id, url)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        mbox = self.__get_mbox_from_content(resp.content)
        for msg in self.__get_msgs_from_mbox(mbox):
            if msg.is_thread_root():
                log.debug("Found message %s thread root: %s.", msg_id, msg.id())
                return msg
        # if root is not found, return initial message as root.
        return initial_msg

    def __get_thread_root(self, msg: Message) -> Message:
        log.debug("Looking for thread root of message %s", msg.id())
        if msg.is_thread_root():
            log.debug("Message is thread root already. Returning.")
            return msg

        parent_id = msg.parent_id()
        if parent_id not in self.messages_cache:
            root = self.__fetch_thread_root(msg)
            if msg.id() != root.id():
                log.debug("Found root message %s for message %s", root.id(), msg.id())
            else:
                log.debug(
                    "Couldn't find root message for %s, using it as root", msg.id())
            return root

        while True:
            log.debug("Parent is %s", parent_id)
            assert parent_id in self.messages_cache
            parent = self.messages_cache[parent_id]
            if parent.is_thread_root():
                log.debug("Parent is the thread root, returning.")
                return parent

            parent_id = parent.parent_id()
            if parent_id not in self.messages_cache:
                root = self.__fetch_thread_root(msg)
                if msg.id() != root.id():
                    log.debug(
                        "Found root message %s for message %s", root.id(), msg.id())
                else:
                    log.debug(
                        "Couldn't find root message for %s, using it as root", msg.id())
                return root

    def __fetch_all_threads(self, since: Date, until: Date) -> list[Message]:
        since_str = since.date.isoformat()
        until_str = until.date.isoformat()

        log.info("Fetching all mails on server %s from %s between %s and %s",
                 self.url, self.user, since_str, until_str)
        mbox_url = self.__get_url(
            f"export/latest.mbox.gz?start={since_str}&end={until_str}"
            )
        log.debug("Downloading mbox at %s", mbox_url)
        resp = requests.get(
            mbox_url,
            timeout=self.timeout
            )
        resp.raise_for_status()

        if not resp.ok:
            log.error("Response is not ok: %s", str(resp))
            return []

        mbox = self.__get_mbox_from_content(resp.content)
        return self.__get_msgs_from_mbox(mbox)

    def get_all_threads(self, since: Date, until: Date):
        log.debug("Fetching all threads since %s until %s.", since, until)
        if (since, until) not in self.threads_cache:
            self.threads_cache[(since, until)] = self.__fetch_all_threads(since, until)

        assert (since, until) in self.threads_cache

        found = []
        for msg in self.threads_cache[(since, until)]:
            msg_id = msg.id()
            if msg_id in found:
                continue

            if not msg.is_from_user(self.user.email):
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
            "Searching for new threads on %s started by %s",
            self.parent.url,
            self.user)

        self.stats = [
            msg
            for msg in self.parent.hyperkitty.get_all_threads(
                self.options.since, self.options.until)
            if msg.is_from_user(self.user.email)
            and msg.is_between_dates(self.options.since, self.options.until)
            ]

    def show(self):
        if not self.error and not self.stats:
            return

        self.header()
        for msg in self.stats:
            self.parent.hyperkitty.print_msg(self.options, msg)


class ThreadsInvolved(Stats):
    """ Mail threads involved in """

    def fetch(self):
        log.info(
            "Searching for mail threads on %s where %s was involved",
            self.parent.url,
            self.user)

        self.stats = [
            msg
            for msg in self.parent.hyperkitty.get_all_threads(
                self.options.since, self.options.until)
            if not msg.is_from_user(self.user.email)
            or not msg.is_between_dates(self.options.since, self.options.until)
            ]

    def show(self):
        if not self.error and not self.stats:
            return

        self.header()
        for msg in self.stats:
            self.parent.hyperkitty.print_msg(self.options, msg)


class HyperkittyStats(StatsGroup):
    """ Hyperkitty Mailing List Archive """

    order = 760

    def __init__(self, option, name=None, parent=None, user=None):
        StatsGroup.__init__(self, option, name, parent, user)

        config = dict(Config().section(option))
        try:
            self.url = config["url"]
        except KeyError as key_err:
            raise ReportError(f"No url in the [{option}] section.") from key_err

        self.hyperkitty = Hyperkitty(self.parent, self.user, self.url,
                                     timeout=config.get("timeout"))
        self.stats = [
            ThreadsStarted(option=f"{option}-started", parent=self),
            ThreadsInvolved(option=f"{option}-involved", parent=self),
            ]
