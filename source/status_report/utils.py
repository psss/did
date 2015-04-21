# coding: utf-8
""" Comfortably generate reports - Utils """

from __future__ import absolute_import

import ConfigParser
import os
import re
import sys
import nitrate

log = nitrate.log
pretty = nitrate.pretty
listed = nitrate.listed

CONFIG = os.path.expanduser("~/.status-report")
MAX_WIDTH = 79

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utils
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def eprint(text):
    """ Print (optionaly encoded) text """
    # When there's no terminal we need to explicitly encode strings.
    # Otherwise this would cause problems when redirecting output.
    print((text if sys.stdout.isatty() else text.encode("utf8")))


def header(text):
    """ Show text as a header. """
    eprint(u"\n{0}\n {1}\n{0}".format(79 * "~", text))


def shorted(text, width=79):
    """ Shorten text, make sure it's not cut in the middle of a word """
    if len(text) <= width:
        return text
    # We remove any word after first overlapping non-word character
    return u"{0}...".format(re.sub(r"\W+\w*$", "", text[:width - 2]))


def item(text, level=0, options=None):
    """ Print indented item. """
    # Extra line before in each section (unless brief)
    if level == 0 and not options.brief:
        print('')
    # Only top-level items displayed in brief mode
    if level == 1 and options.brief:
        return
    # Four space for each level, additional space for wiki format
    indent = level * 4
    if options.format == "wiki" and level == 0:
        indent = 1
    # Shorten the text if necessary to match the desired maximum width
    width = options.width - indent - 2 if options.width else 333
    eprint(u"{0}* {1}".format(u" " * indent, shorted(unicode(text), width)))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Config
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Config(object):
    """ User config file """

    def __init__(self):
        """ Read the config file. """
        self.parser = ConfigParser.SafeConfigParser()
        self.parser.read([CONFIG])

    @property
    def user(self):
        try:
            return self.parser.get("general", "user").split(", ")
        except ConfigParser.NoOptionError:
            return []

    @property
    def email(self):
        try:
            return self.parser.get("general", "email").split(", ")
        except ConfigParser.NoOptionError:
            return []

    @property
    def width(self):
        """ Maximum width of the report """
        try:
            return int(self.parser.get("general", "width"))
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return MAX_WIDTH

    @property
    def grades(self):
        """ Include bug grades """
        try:
            value = self.parser.get("general", "grades")
            return value == '1' or value.lower() == 'true'
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
            return False

    def sections(self, kind=None):
        """ Return all sections (optionally of given kind only) """
        result = []
        for section in self.parser.sections():
            # Selected kind only if provided
            if kind is not None:
                try:
                    section_type = self.parser.get(section, "type")
                    if section_type != kind:
                        continue
                except ConfigParser.NoOptionError:
                    # Implicit header/footer type for backward compatibility
                    if (section == kind == "header" or
                            section == kind == "footer"):
                        pass
                    else:
                        continue
            result.append(section)
        return result

    def section(self, section, skip=None):
        """ Return section items, skip selected (type/order by default) """
        if skip is None:
            skip = ['type', 'order']
        return [(key, val) for key, val in self.parser.items(section)
                if key not in skip]

    def item(self, section, it):
        """ Return content of given item in selected section """
        for key, value in self.section(section, skip=['type']):
            if key == it:
                return value
        raise ConfigError(
            "Item '{0}' not found in section '{1}'".format(it, section))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Exceptions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class ConfigError(Exception):
    """ General problem with configuration file """
    pass


class ReportsError(Exception):
    """ General problem with report generation """
    pass
