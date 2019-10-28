# coding: utf-8

""" Test Metadata Utilities """

from click import style, echo, wrap_text
from yaml import FullLoader

from collections import OrderedDict
import unicodedata
import subprocess
import fmf.utils
import pprint
import shlex
import yaml
import re
import io
import os

log = fmf.utils.Logging('tmt').logger

# Default workdir root and max
WORKDIR_ROOT = '/var/tmp/tmt'
WORKDIR_MAX = 1000

# Hierarchy indent
INDENT = '    '

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Common
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class Common(object):
    """
    Common shared stuff

    Takes care of command line context and workdir handling.
    """

    # Command line context, workdir and status
    _context = None
    _workdir = None

    def __init__(self, parent=None, name=None):
        """ Initialize name and relation with the parent object """
        # Use lowercase class name as the default name
        self.name = name or self.__class__.__name__.lower()
        self.parent = parent

    def __str__(self):
        """ Name is the default string representation """
        return self.name

    @classmethod
    def _opt(cls, option, default=None):
        """ Get an option from the command line context (class version) """
        if cls._context is None:
            return None
        return cls._context.params.get(option, default)

    def opt(self, option, default=None):
        """
        Get an option from the command line context

        Checks also parent options. For flags (boolean values) parent's
        True wins over child's False (e.g. run --verbose enables verbose
        mode for all included plans and steps).
        """
        # Check local option
        local = None
        if self._context is not None:
            local = self._context.params.get(option, default)
        # Check parent option
        parent = None
        if self.parent:
            parent = self.parent.opt(option, default)
        # Special handling for flags (parent's yes wins)
        if isinstance(parent, bool):
            return parent if parent else local
        return parent if parent is not None else local

    def _level(self):
        """ Hierarchy level """
        if self.parent is None:
            return -1
        else:
            return self.parent._level() + 1

    def _indent(self, key, value=None, color=None, shift=0):
        """ Indent message according to the object hierarchy """
        if color is not None:
            key = style(key, fg=color)
        if value is None:
            message = key
        else:
            message = f'{key}: {value}'
        echo(INDENT * (self._level() + shift) + message)

    def info(self, key, value=None, color=None, shift=0):
        """ Show a message unless in quiet mode """
        if not self.opt('quiet'):
            self._indent(key, value, color, shift)

    def verbose(self, key, value=None, color=None, shift=0):
        """ Show message if in verbose or debug mode """
        if self.opt('verbose') or self.opt('debug'):
            self._indent(key, value, color, shift)

    def debug(self, key, value=None, color=None, shift=1):
        """ Show message if in debug mode """
        if self.opt('debug'):
            self._indent(key, value, color, shift)

    def run(self, command, message=None, cwd=None):
        """ Run command in the workdir, give message, handle errors """
        # Use a generic message if none given, prepare error message
        if not message:
            message = "Run command '{}'.".format(
                ' '.join(command) if isinstance(command, list) else command)
        self.debug(message)
        message = "Failed to " + message[0].lower() + message[1:]

        # Nothing more to do in dry mode
        if self.opt('dry'):
            return

        # Split the command if needed
        if isinstance(command, str):
            command = command.split()
        try:
        # Open log and run the command
            with open(os.path.join(self.workdir, 'log.txt'), 'a') as log:
                process = subprocess.Popen(
                    command, cwd=cwd or self.workdir,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                debug = self.opt('debug')
                while process.poll() is None:
                    line = process.stdout.readline().decode('utf-8')
                    if line != '':
                        log.write(line)
                        log.flush()
                        self.debug('out', line.rstrip('\n'), 'yellow')

                    line = process.stderr.readline().decode('utf-8')
                    if line != '':
                        log.write(line)
                        log.flush()
                        self.debug('err', line.rstrip('\n'), 'yellow')
        except OSError as error:
            raise GeneralError(f"{message}\n{error}")

        # Handle the exit code
        if process.returncode != 0:
            raise GeneralError(message)

    def read(self, path):
        """ Read a file from the workdir """
        path = os.path.join(self.workdir, path)
        self.debug(f"Read file '{path}'.")
        try:
            with open(path) as data:
                return data.read()
        except OSError as error:
            raise GeneralError(f"Failed to read '{path}'.\n{error}")

    def write(self, path, data):
        """ Write a file to the workdir """
        path = os.path.join(self.workdir, path)
        self.debug(f"Write file '{path}'.")
        # Dry mode
        if self.opt('dry'):
            return
        try:
            with open(path, 'w') as target:
                return target.write(data)
        except OSError as error:
            raise GeneralError(f"Failed to write '{path}'.\n{error}")

    def status(self, status=None):
        """ Get and set current status, store in workdir """
        # Check for valid values
        if status and status not in ['todo', 'done', 'going']:
            raise GeneralError(f"Invalid status '{status}'.")
        # Store status
        if status:
            self.write('status.txt', status + '\n')
        # Read status
        else:
            try:
                return self.read('status.txt').strip()
            except GeneralError:
                return None

    def _workdir_init(self, id_):
        """
        Initialize the work directory

        Workdir under WORKDIR_ROOT is used/created if 'id' is provided.
        If 'id' is a path, that directory is used instead. Otherwise a
        new workdir is created under WORKDIR_ROOT.
        """
        # Construct the workdir
        if id_ is not None:
            # Use provided directory if path given
            if '/' in id_:
                workdir = id_
            # Construct directory name under workdir root
            else:
                if isinstance(id_, int):
                    id_ = str(id_).rjust(3, '0')
                directory = 'run-{}'.format(id_)
                workdir = os.path.join(WORKDIR_ROOT, directory)
        else:
            # Generate a unique run id
            for id_ in range(1, WORKDIR_MAX + 1):
                directory = 'run-{}'.format(str(id_).rjust(3, '0'))
                workdir = os.path.join(WORKDIR_ROOT, directory)
                if not os.path.exists(workdir):
                    break
            if id_ == WORKDIR_MAX:
                raise GeneralError(
                    "Cleanup the '{}' directory.".format(WORKDIR_ROOT))

        # Create the workdir
        create_directory(workdir, 'workdir', quiet=True)
        self._workdir = workdir

    @property
    def workdir(self):
        """ Get the workdir, create if does not exist """
        if self._workdir is None:
            # Need the parent workdir
            if self.parent is None:
                raise GeneralError('Parent workdir not available')
            # Append name and create
            self._workdir = os.path.join(
                self.parent.workdir, self.name.lstrip('/'))
            create_directory(self._workdir, 'workdir', quiet=True)
        return self._workdir

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Exceptions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class GeneralError(Exception):
    """ General error """

class SpecificationError(GeneralError):
    """ Metadata specification error """

class ConvertError(GeneralError):
    """ Metadata conversion error """

class StructuredFieldError(GeneralError):
    """ StructuredField parsing error """

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  Utilities
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def ascii(text):
    """ Transliterate special unicode characters into pure ascii """
    try:
        if not isinstance(text, unicode):
            text = unicode(text)
    except NameError:
        if not isinstance(text, str):
            text = str(text)
    return unicodedata.normalize('NFKD', text).encode('ascii','ignore')


def variables_to_dictionary(variables):
    """
    Convert shell-like variables into a dictionary

    Accepts single string or list of strings. Allowed forms are:
    'X=1'
    'X=1 Y=2 Z=3'
    ['X=1', 'Y=2', 'Z=3']
    ['X=1 Y=2 Z=3', 'A=1 B=2 C=3']
    'TXT="Some text with spaces in it"'
    """
    if not isinstance(variables, list):
        variables = [variables]
    result = dict()
    for variable in variables:
        if variable is None:
            continue
        for var in shlex.split(variable):
            matched = re.match("([^=]+)=(.*)", var)
            if not matched:
                raise GeneralError("Invalid parameter {0}".format(var))
            name, value = matched.groups()
            result[name] = value
    return result


def dictionary_to_yaml(data):
    """ Convert dictionary into yaml """
    output = io.StringIO()
    yaml.safe_dump(
        data, output,
        encoding='utf-8', allow_unicode=True,
        indent=4, default_flow_style=False)
    return output.getvalue()


def dict_to_shell(data):
    """ Convert dictionary to list of key=value pairs """
    return [f"{key}={shlex.quote(str(value))}" for key, value in data.items()]


def verdict(decision, comment=None, good='pass', bad='fail', problem='warn'):
    """
    Return verdict in green or red based on the decision

    0 or False ... good (green)
    1 or True .... bad (red)
    otherwise .... problem (yellow)
    """

    if decision == 0:
        text = style(bad, fg='red')
    elif decision == 1:
        text = style(good, fg='green')
    else:
        text = style(problem, fg='yellow')
    if comment:
        return text + ' ' + comment
    else:
        return text


def format(
        key, value=None,
        indent=12, width=72, wrap=True,
        key_color='green', value_color='black'):
    """ Nicely format and indent a key-value pair """
    indent_string = (indent + 1) * ' '
    # Key
    output = '{} '.format(str(key).rjust(indent, ' '))
    if key_color is not None:
        output = style(output, fg=key_color)
    # Bool
    if isinstance(value, bool):
        output += ('yes' if value else 'no')
    # List
    elif isinstance(value, list):
        listed_text = fmf.utils.listed(value)
        has_spaces = any([item.find(' ') > -1 for item in value])
        # Use listed output only for short lists without spaces
        if len(listed_text) < width - indent and not has_spaces:
            output += listed_text
        # Otherwise just place each item on a new line
        else:
            output += ('\n' + indent_string).join(value)
    # Text
    elif isinstance(value, str):
        if wrap:
            output += (wrap_text(
                value, width=width,
                preserve_paragraphs=True,
                initial_indent=indent_string,
                subsequent_indent=indent_string).lstrip())
        else:
            output += (('\n' + indent_string).join(
                value.rstrip().split('\n')))
    else:
        output += str(value)
    return output


def create_directory(path, name, quiet=False):
    """ Create a new directory, handle errors """
    say = log.debug if quiet else echo
    if os.path.isdir(path):
        say("Directory '{}' already exists.".format(path))
        return
    try:
        os.makedirs(path, exist_ok=True)
        say("Directory '{}' created.".format(path))
    except OSError as error:
        raise GeneralError("Failed to create {} '{}' ({})".format(
            name, path, error))


def create_file(path, content, name, force=False, mode=0o664, quiet=False):
    """ Create a new file, handle errors """
    say = log.debug if quiet else echo
    action = 'created'
    if os.path.exists(path):
        if force:
            action = 'overwritten'
        else:
            raise GeneralError("File '{}' already exists.".format(path))
    try:
        with open(path, 'w') as file_:
            file_.write(content)
        say("{} '{}' {}.".format(name.capitalize(), path, action))
    except OSError as error:
        raise GeneralError("Failed to create {} '{}' ({})".format(
            name, path, error))

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#  StructuredField
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class StructuredField(object):
    """
    Handling multiple text data in a single text field

    The StructuredField allows you to easily store and extract several
    sections of text data to/from a single text field. The sections are
    separated by section names in square brackets and can be hosted in
    other text as well.

    The section names have to be provided on a separate line and there
    must be no leading/trailing white space before/after the brackets.
    The StructuredField supports two versions of the format:

    Version 0: Simple, concise, useful when neither the surrounding text
    or the section data can contain lines which could resemble section
    names. Here's an example of a simple StructuredField::

        Note written by human.

        [section-one]
        Section one content.

        [section-two]
        Section two content.

        [section-three]
        Section three content.

        [end]

        Another note written by human.

    Version 1: Includes unique header to prevent collisions with the
    surrounding text and escapes any section-like lines in the content::

        Note written by human.

        [structured-field-start]
        This is StructuredField version 1. Please, edit with care.

        [section-one]
        Section one content.

        [section-two]
        Section two content.
        [structured-field-escape][something-resembling-section-name]

        [section-three]
        Section three content.

        [structured-field-end]

        Another note written by human.

    Note that an additional empty line is added at the end of each
    section to improve the readability. This line is not considered
    to be part of the section content.

    Besides handling the whole section content it's also possible to
    store several key-value pairs in a single section, similarly as in
    the ini config format::

        [section]
        key1 = value1
        key2 = value2
        key3 = value3

    Provide the key name as the optional argument 'item' when accessing
    these single-line items. Note that the section cannot contain both
    plain text data and key-value pairs.

    Example::

        field = qe.StructuredField()
        field.set("project", "Project Name")
        field.set("details", "somebody", "owner")
        field.set("details", "2013-05-27", "started")
        field.set("description", "This is a description.\\n"
                "It spans across multiple lines.\\n")
        print field.save()

            [structured-field-start]
            This is StructuredField version 1. Please, edit with care.

            [project]
            Project Name

            [details]
            owner = somebody
            started = 2013-05-27

            [description]
            This is a description.
            It spans across multiple lines.

            [structured-field-end]

        field.version(0)
        print field.save()

            [project]
            Project Name

            [details]
            owner = somebody
            started = 2013-05-27

            [description]
            This is a description.
            It spans across multiple lines.

            [end]

    Multiple values for the same key are supported as well. Enable this
    feature with 'multi=True' when initializing the structured field.
    If multiple values are present their list will be returned instead
    of a single string. Similarly use list for setting multiple values::

        field = qe.StructuredField(multi=True)
        requirements = ['hypervisor=', 'labcontroller=lab.example.com']
        field.set("hardware", requirements, "hostrequire")
        print field.save()

            [structured-field-start]
            This is StructuredField version 1. Please, edit with care.

            [hardware]
            hostrequire = hypervisor=
            hostrequire = labcontroller=lab.example.com

            [structured-field-end]

        print field.get("hardware", "hostrequire")

            ['hypervisor=', 'labcontroller=lab.example.com']
    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #  StructuredField Special
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __init__(self, text=None, version=1, multi=False):
        """ Initialize the structured field """
        self.version(version)
        self._header = ""
        self._footer = ""
        self._sections = {}
        self._order = []
        self._multi = multi
        if text is not None:
            self.load(text)

    def __iter__(self):
        """ By default iterate through all available sections """
        for section in self._order:
            yield section

    def __nonzero__(self):
        """ True when any section is defined """
        return len(self._order) > 0

    __bool__ = __nonzero__

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #  StructuredField Private
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _load_version_zero(self, text):
        """ Load version 0 format """
        # Attempt to split the text according to the section tag
        section = re.compile(r"\n?^\[([^\]]+)\]\n", re.MULTILINE)
        parts = section.split(text)
        # If just one part ---> no sections present, just plain text
        if len(parts) == 1:
            self._header = parts[0]
            return
        # Pick header & footer, make sure [end] tag is present
        self._header = parts[0]
        self._footer = re.sub("^\n", "", parts[-1])
        if parts[-2] != "end":
            raise StructuredFieldError("No [end] section tag found")
        # Convert to dictionary and save the order
        keys = parts[1:-2:2]
        values = parts[2:-2:2]
        for key, value in zip(keys, values):
            self.set(key, value)

    def _load(self, text):
        """ Load version 1+ format """
        # The text must exactly match the format
        format = re.compile(
                r"(.*)^\[structured-field-start\][ \t]*\n"
                r"(.*)\n\[structured-field-end\][ \t]*\n(.*)",
                re.DOTALL + re.MULTILINE)
        # No match ---> plain text or broken structured field
        matched = format.search(text)
        if not matched:
            if "[structured-field" in text:
                raise StructuredFieldError("StructuredField parse error")
            self._header = text
            log.debug("StructuredField not found, treating as a plain text")
            return
        # Save header & footer (remove trailing new lines)
        self._header = re.sub("\n\n$", "\n", matched.groups()[0])
        if self._header:
            log.debug(u"Parsed header:\n{0}".format(self._header))
        self._footer = re.sub("^\n", "", matched.groups()[2])
        if self._footer:
            log.debug(u"Parsed footer:\n{0}".format(self._footer))
        # Split the content on the section names
        section = re.compile(r"\n\[([^\]]+)\][ \t]*\n", re.MULTILINE)
        parts = section.split(matched.groups()[1])
        # Detect the version
        try:
            self.version(int(re.search(
                r"version (\d+)", parts[0]).groups()[0]))
            log.debug("Detected StructuredField version {0}".format(
                    self.version()))
        except AttributeError:
            log.error(parts[0])
            raise StructuredFieldError(
                    "Unable to detect StructuredField version")
        # Convert to dictionary, remove escapes and save the order
        keys = parts[1::2]
        escape = re.compile(r"^\[structured-field-escape\]", re.MULTILINE)
        values = [escape.sub("", value) for value in parts[2::2]]
        for key, value in zip(keys, values):
            self.set(key, value)
        log.debug(u"Parsed sections:\n{0}".format(
            pprint.pformat(self._sections)))

    def _save_version_zero(self):
        """ Save version 0 format """
        result = []
        if self._header:
            result.append(self._header)
        for section, content in self.iterate():
            result.append(u"[{0}]\n{1}".format(section, content))
        if self:
            result.append(u"[end]\n")
        if self._footer:
            result.append(self._footer)
        return "\n".join(result)

    def _save(self):
        """ Save version 1+ format """
        result = []
        # Regular expression for escaping section-like lines
        escape = re.compile(r"^(\[.+\])$", re.MULTILINE)
        # Header
        if self._header:
            result.append(self._header)
        # Sections
        if self:
            result.append(
                    u"[structured-field-start]\n"
                    u"This is StructuredField version {0}. "
                    u"Please, edit with care.\n".format(self._version))
            for section, content in self.iterate():
                result.append(u"[{0}]\n{1}".format(section,
                        escape.sub("[structured-field-escape]\\1", content)))
            result.append(u"[structured-field-end]\n")
        # Footer
        if self._footer:
            result.append(self._footer)
        return "\n".join(result)

    def _read_section(self, content):
        """ Parse config section and return ordered dictionary """
        dictionary = OrderedDict()
        for line in content.split("\n"):
            # Remove comments and skip empty lines
            line = re.sub("#.*", "", line)
            if re.match(r"^\s*$", line):
                continue
            # Parse key and value
            matched = re.search("([^=]+)=(.*)", line)
            if not matched:
                raise StructuredFieldError(
                    "Invalid key/value line: {0}".format(line))
            key = matched.groups()[0].strip()
            value = matched.groups()[1].strip()
            # Handle multiple values if enabled
            if key in dictionary and self._multi:
                if isinstance(dictionary[key], list):
                    dictionary[key].append(value)
                else:
                    dictionary[key] = [dictionary[key], value]
            else:
                dictionary[key] = value
        return dictionary

    def _write_section(self, dictionary):
        """ Convert dictionary into a config section format """
        section = ""
        for key in dictionary:
            if isinstance(dictionary[key], list):
                for value in dictionary[key]:
                    section += "{0} = {1}\n".format(key, value)
            else:
                section += "{0} = {1}\n".format(key, dictionary[key])
        return section

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #  StructuredField Methods
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def iterate(self):
        """ Return (section, content) tuples for all sections """
        for section in self:
            yield section, self._sections[section]

    def version(self, version=None):
        """ Get or set the StructuredField version """
        if version is not None:
            if version in [0, 1]:
                self._version = version
            else:
                raise StructuredFieldError(
                        "Bad StructuredField version: {0}".format(version))
        return self._version

    def load(self, text, version=None):
        """ Load the StructuredField from a string """
        if version is not None:
            self.version(version)
        # Make sure we got a text, convert to unicode if necessary
        try:
            if not isinstance(text, basestring):
                raise StructuredFieldError(
                        "Invalid StructuredField, expecting string or unicode")
            if not isinstance(text, unicode):
                text = text.decode("utf8")
        except NameError:
            if not isinstance(text, str):
                raise StructuredFieldError(
                        "Invalid StructuredField, expecting string")
        # Remove possible carriage returns
        text = re.sub("\r\n", "\n", text)
        # Make sure the text has a new line at the end
        if text and text[-1] != "\n":
            text += "\n"
        log.debug(u"Parsing StructuredField\n{0}".format(text))
        # Parse respective format version
        if self._version == 0:
            self._load_version_zero(text)
        else:
            self._load(text)

    def save(self):
        """ Convert the StructuredField into a string """
        if self.version() == 0:
            return self._save_version_zero()
        else:
            return self._save()

    def header(self, content=None):
        """ Get or set the header content """
        if content is not None:
            self._header = content
        return self._header

    def footer(self, content=None):
        """ Get or set the footer content """
        if content is not None:
            self._footer = content
        return self._footer

    def sections(self):
        """ Get the list of available sections """
        return self._order

    def get(self, section, item=None):
        """ Return content of given section or section item """
        try:
            content = self._sections[section]
        except KeyError:
            raise StructuredFieldError(
                    "Section [{0}] not found".format(ascii(section)))
        # Return the whole section content
        if item is None:
            return content
        # Return only selected item from the section
        try:
            return self._read_section(content)[item]
        except KeyError:
            raise StructuredFieldError(
                    "Unable to read '{0}' from section '{1}'".format(
                    ascii(item), ascii(section)))

    def set(self, section, content, item=None):
        """ Update content of given section or section item """
        # Convert to string if necessary, keep lists untouched
        if not isinstance(content, list):
            try:
                if not isinstance(content, basestring):
                    content = unicode(content)
                elif not isinstance(content, unicode):
                    content = content.decode("utf8")
            except:
                if not isinstance(content, str):
                    content = str(content)
        # Set the whole section content
        if item is None:
            # Add new line if missing
            if content and content[-1] != "\n":
                content += "\n"
            self._sections[section] = content
        # Set only selected item from the section
        else:
            try:
                current = self._sections[section]
            except KeyError:
                current = ""
            dictionary = self._read_section(current)
            dictionary[item] = content
            self._sections[section] = self._write_section(dictionary)
        # Remember the order when adding a new section
        if section not in self._order:
            self._order.append(section)

    def remove(self, section, item=None):
        """ Remove given section or section item """
        # Remove the whole section
        if item is None:
            try:
                del self._sections[section]
                del self._order[self._order.index(section)]
            except KeyError:
                raise StructuredFieldError(
                        "Section [{0}] not found".format(ascii(section)))
        # Remove only selected item from the section
        else:
            try:
                dictionary = self._read_section(self._sections[section])
                del(dictionary[item])
            except KeyError:
                raise StructuredFieldError(
                        "Unable to remove '{0}' from section '{1}'".format(
                        ascii(item), ascii(section)))
            self._sections[section] = self._write_section(dictionary)
