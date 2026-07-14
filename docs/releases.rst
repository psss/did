.. _releases:

======================
    Releases
======================


did-0.24
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first day of the week is now **configurable** via the
``week_start`` option in the ``[general]`` config section. This
is useful for teams and regions where the week starts on Sunday
or another day. Flexible matching is supported — full names or
three-letter abbreviations like ``sun`` or ``mon`` work.

The ``--width 0`` option can be used to produce reports with
unlimited line width.

Tokens can now be fetched from an **external command** using the
new ``token_command`` config option, enabling integration with
password managers such as 1Password or BitWarden. The option is
supported by all plugins that use token authentication.


did-0.23
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Initial support for the Forgejo_ backend has been added with
stats for **created issues** and **created pull requests**.

Both GitHub and GitLab plugins now track pull/merge requests
**authored by you and successfully merged**, a new stat alongside
the existing created and commented ones.

Jira Cloud is now a first-class citizen with dedicated
authentication and query handling, and Jira issues **with
worklogs** can be collected as well.

A new ``--full-message`` flag lets you include the complete body of
commits, pull requests and merge requests in the report instead of
just the summary line.

The GitLab plugin no longer fetches thousands of pages when the API
returns a large result set, and the default 60-second timeout has
been fixed. GitHub error responses are now handled gracefully, and
the ``commented_in_range`` filter works correctly.

Parsing of the ``--config`` argument with whitespace has been
fixed.

Significant **typing and test coverage** improvements across the
codebase: type hints have been added to ``base.py``, ``cli.py``,
``conftest.py``, and the Jira, Confluence, Bugzilla, Bodhi and
items plugins. New unit test suites cover the ``utils`` and
``stats`` modules. Python 3.14 is now supported.

.. _Forgejo: https://forgejo.org/


did-0.22
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``did last monday`` through ``did last sunday`` syntax now
works for quickly selecting a single past day by name.

Stats collection now runs **in parallel** using a thread pool,
which noticeably speeds up reports that query many backends. The
report is completed even when individual plugins encounter errors.

The GitHub plugin gains support for filtering by ``user``,
``org`` and ``repo``, an ``exclude_org`` option, and properly
collects comments.

The Jira plugin received substantial improvements in this release.
A new ``transition`` stat tracks issues that moved between states.
Updated issues and issues resolved by a tester or contributor can
now be collected, and timeout handling for batch fetches has been
improved. Rate limiting is handled automatically with retry logic
in both the Jira and GitHub plugins.

Confluence picks up token-based authentication and a new stat for
**modified pages**. Markdown output is now supported in the
Google and Koji plugins.

The Pagure plugin handles timeouts and server errors more
gracefully, and closed pull requests are now tracked.  A new stat
for **comments on Pagure** issues has been added.

New plugins have been added for searching public mailing list
archives: **public-inbox** via `public-inbox`_ and
**hyperkitty** via Hyperkitty_.

Numerous **pylint and code quality** fixes have been applied
across the codebase. Pre-commit hooks have been updated and the
test suite now runs in parallel with ``pytest-xdist``.

.. _public-inbox: https://public-inbox.org/
.. _Hyperkitty: https://gitlab.com/mailman/hyperkitty


did-0.21
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new ``--format=markdown`` option has been added, providing
**Markdown output** alongside the existing plain text and wiki
formats. The Bodhi and Pagure plugins include Markdown support
as well.

Header and footer sections now support defining **subitems**, so
that recurring subsections can be pre-filled in the report
template.

The Google plugin setup instructions have been refreshed and the
``sphinx_rtd_theme`` is now used for the documentation.
