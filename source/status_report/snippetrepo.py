#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Comfortably archive task snippets locally """

from dateutil.parser import parse as dt_parse
import re

from status_report.utils import log, info, Date, EMAIL_REGEXP

import sqlalchemy as sqla
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

MAX_WIDTH = 50  # FIXME is this reasonable? 140? 79?
TODAY = str(Date("today"))
SNIPPET_RE = re.compile(r'^(\d\d\d\d-\d\d-\d\d)?(.*)')
AT_RE = re.compile('\^({0})'.format(EMAIL_REGEXP.pattern))
TAG_RE = re.compile('\#(\w+)')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Snippets Repository
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class SnippetsRepo(object):
    backend = None
    uri = None
    _snippets = None

    def __init__(self, snippets=None, uri=None, debug=None, email=None,
                 topic=None):
        self._snippets = snippets or []
        self.uri = uri
        self.debug = bool(debug or False)
        self.email = email
        self.topic = topic

    def __len__(self):
        return len(self._snippets)

    def __getitem__(self, i):
        return self._snippets[i]

    def parse_snippets(self, snippets, as_type=None):
        _snippets = []
        if not snippets:
            log.warn('Tried parsing empty snippets and failed')
        else:
            for snippet in snippets:
                # simplify spacing
                snippet = re.sub('\s+', ' ', snippet)
                snippet = self.parse_snippet(snippet, as_type=as_type)
                _snippets.append(snippet)
            # REPLACES existing store!!! GOOD IDEA?
        self._snippets = _snippets

    def parse_snippet(self, snippet, as_type=None):
        # search for a date override in the beginning of each snippet
        # otherwise default to completion date of 'today'
        search = SNIPPET_RE.search(snippet)
        if not search:
            log.error('Failed to parse snippet as expected!')
            raise RuntimeError

        # default to TODAY if no on_date is set in-line
        on_date = dt_parse(search.group(1) or TODAY)
        text = search.group(2).strip()

        if not text:
            log.debug('Found empty snippet!')
            return  # skip empty snippets

        # space separated ^emails
        search = AT_RE.findall(snippet)
        at_csv = [', '.join(s[0].split(' '))
                  for s in search if s][0] if search else ''
        # #Tags
        search = TAG_RE.findall(snippet)
        tag_csv = [', '.join([x.rstrip('#') for x in s[0].split(' ')])
                   for s in search if s][0] if search else ''

        owner_email = self.email


        # Make sure each snippest has an on_date

        _snippet = {
            'on_date': on_date,
            'text': text,
            'owner_email': owner_email,
            'at_csv': at_csv,
            'tag_csv': tag_csv,
            'topic': self.topic,
        }

        if as_type is str:
            snippet = (
                '{on_date} {owner_email} {at_csv} {text} {tag_csv}'.format(
                    **_snippet))
        else:
            snippet = _snippet
        return snippet

    def __str__(self):
        return str('\n'.join(self._snippets))

    def __delitem__(self, i):
        raise NotImplemented("OOps! Can not remove Snippets!")

    def insert(self, i, v):
        raise NotImplemented("OOps! Can not insert Snippets!")

    def write(self, *args, **kwargs):
        k = len(self._snippets)
        log.debug('Writing {0} snippets to {1}'.format(k, self.uri))

    # FIXME: RENAME TO LS()
    def snippets(self, *args, **kwargs):
        raise NotImplementedError("Must be defined by sub-class")


class SnippetsRepoSQLAlchemy(SnippetsRepo):
    def __init__(self, *args, **kwargs):
        super(SnippetsRepoSQLAlchemy, self).__init__(*args, **kwargs)
        self.engine = sqla.create_engine(self.uri, echo=self.debug)
        self.Session = sqla.orm.sessionmaker(bind=self.engine)

    def write(self):
        super(SnippetsRepoSQLAlchemy, self).write()
        session = self.Session()

        # Make sure the table is available
        Base.metadata.create_all(self.engine)

        for kwargs in iter(self._snippets):
            session.add(Snippet(**kwargs))
        else:
            session.commit()
        info('{0} snippets saved to {1}'.format(len(self), self.uri))

    def snippets(self, topic=None, limit=None):
        session = self.Session()
        q = session.query(Snippet)  # query for all snippets
        if topic:
            q = q.filter(Snippet.topic == topic)
        q = q.order_by(sqla.desc(Snippet.id))  # order in reverse
        q = q.limit(limit) if limit else q  # grab the most recent X LIMIT
        snippets = sorted(q.all(), reverse=True)
        return snippets


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Snippet SQLAlchemy Models
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# FIXME: Exception is hit when SQLite .db isn't created before query

class Snippet(Base):
    '''
    owner_email: email address of the submiter and implied owner
    created_on: autogenerated date created when instance is created
    updated_on: same, but for when the instance is updated
    on_date: date associated with the completion of the snippet
    text: raw snippet text
    topic: FIXME: WHAT IS IT? option?
    tag_csv: csv dump of all tags associated with this instance
    at_csv: csv dump of all people @'d in this instance
    '''
    __tablename__ = 'snippets'

    # FIXME: normalize?
    id = sqla.Column(sqla.Integer, primary_key=True)
    owner_email = sqla.Column(sqla.String(MAX_WIDTH, convert_unicode=True))
    created_on = sqla.Column(sqla.DateTime, default=sqla.func.now())
    updated_on = sqla.Column(
        sqla.DateTime, default=sqla.func.now(), onupdate=sqla.func.now())
    text = sqla.Column(sqla.String(MAX_WIDTH, convert_unicode=True))
    topic = sqla.Column(sqla.String(MAX_WIDTH, convert_unicode=True))
    on_date = sqla.Column(sqla.Date, default=sqla.func.now())
    tag_csv = sqla.Column(sqla.String(512, convert_unicode=True))
    # FIXME: Make these more configurable
    at_csv = sqla.Column(sqla.String(512, convert_unicode=True))

    def __repr__(self):
        return "<Snippet(on_date='{0}', topic='{1}', text='{2}')>".format(
            self.on_date, self.topic, self.text)

    def __str__(self):
        return '{0} {1} {2}'.format(self.on_date, self.topic, self.text)
