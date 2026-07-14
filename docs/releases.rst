.. _releases:

======================
    Releases
======================


did-0.24
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The first day of the week is now **configurable** via the
``week_start`` option in the ``[general]`` config section
(`#474`_). This is useful for teams and regions where the week
starts on Sunday or another day. Flexible matching is supported
— full names or three-letter abbreviations like ``sun`` or
``mon`` work.

The ``--width 0`` option can be used to produce reports with
unlimited line width (`#460`_).

Tokens can now be fetched from an **external command** using the
new ``token_command`` config option, enabling integration with
password managers such as 1Password or BitWarden (`#469`_). The
option is supported by all plugins that use token authentication.

.. _#474: https://github.com/psss/did/pull/474
.. _#460: https://github.com/psss/did/pull/460
.. _#469: https://github.com/psss/did/pull/469


did-0.23
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Initial support for the Forgejo_ backend has been added with
stats for **created issues** and **created pull requests**
(`#452`_).

Both GitHub and GitLab plugins now track pull/merge requests
**authored by you and successfully merged**, a new stat alongside
the existing created and commented ones (`#311`_).

Jira Cloud is now a first-class citizen with dedicated
authentication and query handling (`#448`_), and Jira issues
**with worklogs** can be collected as well (`#429`_).

A new ``--full-message`` flag lets you include the complete body
of commits, pull requests and merge requests in the report
instead of just the summary line (`#446`_).

The GitLab plugin no longer fetches thousands of pages when the
API returns a large result set (`#377`_), and the default
60-second timeout has been fixed (`#421`_). GitHub error
responses are now handled gracefully (`#408`_), and the
``commented_in_range`` filter works correctly (`#444`_).

Parsing of the ``--config`` argument with whitespace has been
fixed (`#437`_).

Significant **typing and test coverage** improvements across the
codebase: type hints have been added to ``base.py``, ``cli.py``,
``conftest.py``, and the Jira, Confluence, Bugzilla, Bodhi and
items plugins. New unit test suites cover the ``utils`` and
``stats`` modules. Python 3.14 is now supported.

.. _Forgejo: https://forgejo.org/
.. _#452: https://github.com/psss/did/pull/452
.. _#311: https://github.com/psss/did/pull/311
.. _#448: https://github.com/psss/did/pull/448
.. _#429: https://github.com/psss/did/pull/429
.. _#446: https://github.com/psss/did/pull/446
.. _#377: https://github.com/psss/did/pull/377
.. _#421: https://github.com/psss/did/pull/421
.. _#408: https://github.com/psss/did/pull/408
.. _#444: https://github.com/psss/did/pull/444
.. _#437: https://github.com/psss/did/pull/437


did-0.22
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``did last monday`` through ``did last sunday`` syntax now
works for quickly selecting a single past day by name (`#342`_).

Stats collection now runs **in parallel** using a thread pool,
which noticeably speeds up reports that query many backends
(`#390`_). The report is completed even when individual plugins
encounter errors.

The GitHub plugin gains support for filtering by ``user``,
``org`` and ``repo`` (`#373`_), an ``exclude_org`` option, and
properly collects comments. Rate limiting is handled
automatically with retry logic in both the GitHub (`#374`_) and
Jira plugins.

The Jira plugin received substantial improvements in this
release. A new ``transition`` stat tracks issues that moved
between states (`#352`_). Updated issues and issues resolved by
a tester or contributor can now be collected, and timeout
handling for batch fetches has been improved.

Confluence picks up token-based authentication (`#365`_) and a
new stat for **modified pages**. Markdown output is now supported
in the Google (`#367`_) and Koji (`#359`_) plugins.

The Pagure plugin handles timeouts and server errors more
gracefully, and closed pull requests are now tracked (`#390`_).
A new stat for **comments on Pagure** issues has been added.

New plugins have been added for searching public mailing list
archives: **public-inbox** (`#329`_) and **hyperkitty**
(`#388`_).

Numerous **pylint and code quality** fixes have been applied
across the codebase. Pre-commit hooks have been updated and the
test suite now runs in parallel with ``pytest-xdist``.

.. _#342: https://github.com/psss/did/pull/342
.. _#390: https://github.com/psss/did/pull/390
.. _#373: https://github.com/psss/did/pull/373
.. _#374: https://github.com/psss/did/pull/374
.. _#352: https://github.com/psss/did/pull/352
.. _#365: https://github.com/psss/did/pull/365
.. _#367: https://github.com/psss/did/pull/367
.. _#359: https://github.com/psss/did/pull/359
.. _#329: https://github.com/psss/did/pull/329
.. _#388: https://github.com/psss/did/pull/388


did-0.21
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new ``--format=markdown`` option has been added, providing
**Markdown output** alongside the existing plain text and wiki
formats (`#315`_). The Bodhi and Pagure plugins include Markdown
support as well.

Header and footer sections now support defining **subitems**, so
that recurring subsections can be pre-filled in the report
template (`#312`_).

.. _#315: https://github.com/psss/did/pull/315
.. _#312: https://github.com/psss/did/pull/312
