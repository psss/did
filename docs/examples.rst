
=================
    Examples
=================

Let's have a look at a couple of real-life examples for ``did``
and ``idid``


Config
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I have created the following config file to track my work on tools
development in git, bug updates in bugzilla, ticket updates in
trac, plus my favorite header & footer I'm used to fill manually::

    [general]
    email = "Petr Šplíchal" <psplicha@redhat.com>
    width = 79

    [joy]
    type = logg
    desc = Joy of the Day

    [header]
    type = header
    high = Highlights

    [tools]
    type = git
    did = /home/psss/git/did
    edd = /home/psss/git/edd

    [trac]
    type = trac
    prefix = TT
    url = https://some.trac.com/trac/project/rpc

    [bz]
    type = bugzilla
    prefix = BZ
    url = https://bugzilla.redhat.com/xmlrpc.cgi

    [footer]
    type = footer
    next = Plans, thoughts, ideas...
    status = Status: Green | Yellow | Orange | Red


Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's how available command line options for ``did`` with this
config. Note that ``did`` detects all configured plugins and 
creates corresponding option groups for each of them::

    usage: did [this|last] [week|month|quarter|year] [options]

    optional arguments:
      -h, --help       show this help message and exit

    Select:
      --email EMAILS   User email address(es)
      --since SINCE    Start date in the YYYY-MM-DD format
      --until UNTIL    End date in the YYYY-MM-DD format

    Header:
      --header-high    Highlights
      --header         All above

    Joy of the Day:
      --joy-loggs
      --joy

    Bugzilla stats:
      --bz-filed       Bugs filed
      --bz-patched     Bugs patched
      --bz-posted      Bugs posted
      --bz-fixed       Bugs fixed
      --bz-returned    Bugs returned
      --bz-verified    Bugs verified
      --bz-commented   Bugs commented
      --bz-closed      Bugs closed
      --bz             All above

    Work on tools:
      --tools-did      Work on did
      --tools-edd      Work on edd
      --tools          All above

    Tickets in trac:
      --trac-created   Tickets created in trac
      --trac-accepted  Tickets accepted in trac
      --trac-updated   Tickets updated in trac
      --trac-closed    Tickets closed in trac
      --trac           All above

    Footer:
      --footer-next    Plans, thoughts, ideas...
      --footer-status  Status: Green | Yellow | Orange | Red
      --footer         All above

    Format:
      --format FORMAT  Output style, possible values: text (default) or wiki
      --width WIDTH    Maximum width of the report output (default: 79)
      --brief          Show brief summary only, do not list individual items
      --verbose        Include more details (like modified git directories)

    Utils:
      --config FILE    Use alternate configuration file (default: 'config')
      --total          Append total stats after listing individual users
      --merge          Merge stats of all users into a single report
      --debug          Turn on debugging output, do not catch exceptions


Usage for ``idid`` is even simpler::

    usage: idid [today|DATE|...] [topic] 'Logg record' [options]

    optional arguments:
      -h, --help      show this help message and exit
      --debug         Turn on debugging output, catch exceptions
      --quiet         Turn off all logging except errors; no exceptions

    Select:
      --email EMAILS  User email address(es)
      --since SINCE   Start date in YYYY-MM-DD format
      --until UNTIL   End date in YYYY-MM-DD format


Week
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now it's easy to find out what I was working on during this week::

    > did
    Status report for this week (2015-09-07 to 2015-09-13).

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     Petr Šplíchal <psplicha@redhat.com>
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    * Highlights

    * Joy of the week
        * @cward submitted a bunch of did pull requests! #ftw

    * Bugs fixed: 2
        * BZ#1261963 - wrong date format causes traceback
        * BZ#1248551 - status-report crashes when trac url is incorrect

    * Work on did: 52 commits
        * 91ae8e7 - Enabled syntax highlighting for config example
        * 978add5 - Convert plugin order list into table
        * 5de5514 - Update welcome page and module documentation
        * 0773a3f - Handle invalid date format
        * 4deb67b - Handle invalid paths in the git plugin config
        * 2aace67 - Handle invalid url in trac plugin configuration
        * 717f9e4 - Consider ticket description change as update
        * e84e0fc - Allow turning off py.test output capture feature
        * 7ae7df1 - Check free command line arguments for typos
        * b4e110e - Include example config in docs, adjust man page
        * d623ef0 - Clarify a bit more did.cli.main() usage
        * 72aaa5d - Move module description to the module itself
        * ...

    * Tickets updated in trac: 2
        * TT#0400 - Convert status-report to an open source project
        * TT#0490 - Add or improve missing test coverage for key use cases

    * Plans, thoughts, ideas...

    * Status: Green | Yellow | Orange | Red


To save additional joys, just run ``idid``::

    > idid joy 'Finished drafting the idid feature'
    > idid joy yesterday 'Cleaned out my inbox'

To retrieve just the joys you've saved for the week, just run ``did``::

    > did this week --joy
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     Petr Šplíchal <psplicha@redhat.com>
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    * Joy of the week
        * Finished drafting the idid feature
        * Cleaned out my inbox


Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

I can check my work on tools development during the last month::

    > did --tools last month
    Status report for the last month (2015-08-01 to 2015-08-31).

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     Petr Šplíchal <psplicha@redhat.com>
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    * Work on did: 3 commits
        * 6167e4f - Adjustments after the stats refactoring
        * 3df5c60 - Include gerrit details as comments, fix exception
        * 6bc869f - Include 'items' plugin config example

    * Work on edd: 13 commits
        * 77d5c94 - Bail out if no file selected with --list [fix #5]
        * eb4db1a - Document the Ctrl-Shift-V keyboard shortcut
        * 1888397 - Version bump and changelog entry for 0.2
        * 2f4b631 - Document new options, some adjustments
        * c18095c - New option --last, some reorganization [fix #1]
        * 437103e - Work around RHEL7 zenity bug [BZ#1060471]
        * 653c7de - Merge new option --list
        * dddbc85 - Use the primary mouse selection first [fix #2]
        * a025c1c - Packaging stuff, documentation update
        * 7b3e9c8 - Detect text editor if not set
        * a1a2b9a - Use 'txt' extension for the temporary file
        * dec9d63 - New option --shortcut for keyboard shortcut
        * 556d3c4 - Include a short usage message


Brief
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It's also possible to list only a concise summary of each section
using the ``--brief`` option or select only desired stats to be
displayed. Special values ``today`` and ``yesterday`` can be used
instead of typing the whole date string::

    > did --bz-filed --bz-fixed --bz-verified --until today --brief
    Status report for given date range (1993-01-01 to 2015-09-11).

    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
     Petr Šplíchal <psplicha@redhat.com>
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    * Bugs filed: 845
    * Bugs fixed: 427
    * Bugs verified: 278

That's it! Now you can experiment yourself ;-)
