#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Comfortably generate reports - Local Snippets """

import re

from status_report.base import Stats, StatsGroup
from status_report.utils import item, Config, Date
from status_report.snippetrepo import SnippetsRepoSQLAlchemy

TODAY = str(Date("today"))
snippet_re = re.compile('^(\d\d\d\d-\d\d-\d\d)?(.*)')


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Snippet Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class Snippets(Stats):
    """ Snippet commits """
    def __init__(self, option, name=None, parent=None, uri=None):
        # WHY DOES THIS BREAK IF IT GOES AFTER THE INIT__??
        super(Snippets, self).__init__(option, name, parent)
        self.uri = uri
        self.repo = SnippetsRepoSQLAlchemy(uri=self.uri)

    def fetch(self):
        self.stats = self.repo.snippets(topic=self.option)

    def header(self):
        """ Show summary header. """
        item(
            "{0}: {1} snippet{2}".format(
                self.name, len(self.stats),
                "" if len(self.stats) == 1 else "s"),
            level=0, options=self.options)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Snippet Stats
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class SnippetStats(StatsGroup):
    """ Snippet stats group """

    # Default order  # FIXME  TOP? OR BOTTOM?
    order = 1000

    def fetch(self):
        for topic, uri in Config().section(self.option):
            name = "Work on {0}".format(topic)
            snippets = Snippets(option=topic, name=name, parent=self, uri=uri)
            snippets.fetch()
            self.stats.append(snippets)
