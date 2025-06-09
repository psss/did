Name: did
Version: 0.22
Release: 1%{?dist}

Summary: What did you do last week, month, year?
License: GPL-2.0-or-later

URL: https://github.com/psss/did
Source0: %{url}/releases/download/%{version}/did-%{version}.tar.bz2

BuildArch: noarch
BuildRequires: git-core
BuildRequires: python3-bodhi-client
BuildRequires: python3-bugzilla
BuildRequires: python3-dateutil
BuildRequires: python3-devel
BuildRequires: python3-httplib2
BuildRequires: python3-pytest
BuildRequires: python3-pytest-xdist
BuildRequires: python3-requests-gssapi
BuildRequires: python3-setuptools
BuildRequires: python3-nitrate
Requires: python3-bugzilla
Requires: python3-httplib2
Requires: python3-nitrate
Requires: python3-requests-gssapi
Requires: python3-feedparser
Requires: python3-tenacity


%description
Comfortably gather status report data (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.

%prep
%autosetup -S git

%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files did
mkdir -p %{buildroot}%{_mandir}/man1
install -pm 644 did.1.gz %{buildroot}%{_mandir}/man1

%check
export LANG=en_US.utf-8
%pytest -vv tests/unit/test*.py -k 'not smoke'

%files -f %{pyproject_files}
%{_mandir}/man1/*
%{_bindir}/did
%doc README.rst examples
%license LICENSE

%changelog
* Tue Jun 03 2025 Petr Šplíchal <psplicha@redhat.com> - 0.22-1
- Implement `transition` stats for the `jira` plugin (#352)
- Fix issue with wrong `until` in GitHub search (#376)
- List resolved jira by tester and contributor field
- Fix `zammad` token bug, some minor adjustments
- Better handling auth max retry in jira plugin
- Handle JSON decode errors in pagure plugin
- Reuse bodhi connection instead of opening new ones
- Properly handle timeout in pagure plugin
- Complete report even on plugin error
- Better handling on server errors for pagure plugin
- Better handling of wrong url in confluence plugin
- Handle timeout fetching batches in jira plugin
- Fixed Jira updated issues and support timeout
- Collect stats in parallel
- Add stats for updated jira tickets
- Handle rate limiting in Jira plugin
- Allow to filter out orgs in GitHub plugin
- Properly collect comments in GitHub
- Improve items plugin
- Enable pagure closed PRs stats collection
- Add hyperkitty support
- Handle better the GitLab expired token case
- Increased test coverage
- Use pytest-xdist for parallelizing test execution
- Add collection of comments for Pagure
- Cover markdown format while testing Koji
- Use tenacity handling retry connection to GitHub
- Added stats for modified pages in Confluence
- Allow to skip SSL verification in bugzilla plugin
- Added markdown support to google plugin
- Add token authentication to confluence plugin
- Add markdown support to koji plugin
- Fetch all created issues correctly in `pagure` (#379)
- Use custom `user-agent` in the `public_inbox` plugin (#392)
- Fix dockerfile executable path, add git to container (#354)
- Support `user`, `org`, `repo` in the `github` plugin (#373)
- Handle the GitHub rate limit in a better way (#374)
- Create a Public Inbox Plugin
- Implement `did last [monday..sunday]`
- Correctly handle merge commits in verbose mode
- Prevent duplicates in github issue stats
- Retry connecting to GitLab API on error
- Add a `Toolbelt Catalog` entry for `did`
- Allow skipping events that are not reportable
- Add a team report example using login aliases
- Migrate to the `SPDX` identifier

* Fri Nov 10 2023 Petr Šplíchal <psplicha@redhat.com> - 0.21-1
- Pass plugin configuration to koji `ClientSession`
- Add `markdown` format output to `bodhi` plugin
- Add `markdown` format output to `pagure` plugin
- Handle connection error fetching gitlab user
- Update instructions for the `google` plugin
- Add `sphinx_rtd_theme` to the list of extensions
- Replace deprecated calls to `warn`
- Fix docs building warnings, pin sphinx version
- Add support for `markdown` format output (#315)
- Move line length recommendation to proper section
- Update pre-commit GH action with latest version
- Add dependency on `python3-feedparser`
- Replace `readfp()` with `read_file()`
- Support defining subitems for header and footer
- Give a reasonable error for unreachable wiki url
- Report Gitlab tasks-commented properly
- Fix typo in section name
- Skip own pull requests in `pull-requests-reviewed`

* Thu Mar 09 2023 Petr Šplíchal <psplicha@redhat.com> - 0.20-1
- Produce fixed `phabricator` statistics
- Address packit warning on the `metadata` key
- Remove the Travis CI configuration
- Fix pytest invocation
- Move common constants to the top of `did.utils`
- Add new configuration options for custom separator
- Fix broken phabricator tests
- Fix potentially uninitialized local variable
- Add CodeQL workflow for GitHub code scanning
- Add comment stats on GitHub issues & pull requests
- Add the `name-tests-test` pre-commit hook
- Add the new `phabricator` plugin
- Update test data for `sentry`, `gitlab` and `gerrit`
- Update `pre-commit` configuration, enable `flake8`
- Allow all plugins to fetch secrets from files
- Update packit config to address recent changes
- Fix typo in the Google plugin docstring
- Speed up local testing, add missing require
- Update google plugin installation instructions
- Koji plugin
- Handle GitHub API rate limit
- Add Github Action for PyPI releases

* Tue Jan 18 2022 Lukáš Zachar <lzachar@redhat.com> - 0.19-1
- Install all required packages during docs building
- Adjust code style to be pep8 compatible
- Update docs for contributors, enable pre-commit
- Add basic support for Zammad
- Check if the GitHub credential token is valid
- Fix jira issues search when user `login` provided
- Add minor clarification note about token name
- Split jira token expiration into two options
- Adjust the support for Jira Personal Access Tokens
- Support Personal Access Token in the Jira plugin
- Return all the bugzilla results from a search
- Install fresh sphinx when building readthedocs
- Adjust the paging support for the GitHub plugin
- Add pagination support for GitHub, fixes #247
- Adjust the new plugin for reporting bodhi updates
- Add a new plugin with support for Bodhi updates
- Use user email for searching updated jira issues
- Adjust the switch from fiscal to calendar year
- Switch from fiscal year to natural year
- Update docs for gitlab, github and confluence
- Give a better message upon jira search failure
- Raise the number of github issues fetched per page

* Mon Apr 19 2021 Petr Šplíchal <psplicha@redhat.com> - 0.18-1
- Support custom xmlrpc endpoint for MoinMoin wiki
- Adjust the approved merge requests for gitlab
- Add search for approved merge requests in gitlab
- Enable copr builds from master, simplify tests
- Add "no prefix" rule to commit message suggestions
- Simplify packit config, enable epel-8 for testing
- Do not use interpolation for ConfigParser
- Expand tilde in config path values
- Fix a typo in the README format section
- Update test data for the gerrit plugin
- Adjust password file support for jira & confluence
- Add password file options for jira and confluence

* Mon Jul 13 2020 Petr Šplíchal <psplicha@redhat.com> - 0.17-1
- Prevent exploring tests under the tmt directory
- Run unit tests always under the English locale
- Enable basic smoke test against github in packit
- Disable test for the redmine plugin
- Update test data for the redmine plugin
- Update test data for the sentry plugin
- Update test data for the gerrit plugin
- Use calendar year quarters by default [fix #223]
- Merge the improved Jira search [#198]
- Adjust improved Jira search using scriptrunner
- Use scriptrunner issueFunction to speed up things
- Simplify Packit config (copr_build no more needed)
- Update test data for the sentry plugin
- Implement Jira issue comparison to prevent dupes
- Do not break sorting on merge
- Add default command into the info log [fix #217]
- Enable Python 3.8 in Travis, update metadata

* Tue Dec 10 2019 Petr Šplíchal <psplicha@redhat.com> - 0.16-1
- Convert smoke test into docs test, fix config file
- Include a short summary in the help usage message
- Enable simple smoke test in the testing farm
- Add nitrate back into the package requires
- Enable custom tarball in Packit to fix man page
- Mention custom plugins config on the plugins page
- Enable copr builds and add packit config
- Custom eprint() is no more necessary [fix #211]
- Convert custom section order to int [fix #212]

* Thu Nov 14 2019 Petr Šplíchal <psplicha@redhat.com> - 0.15-1
- Create a single StatsGroup for 'items' [fix #208]
- Google plugin __unicode__ leftover

* Tue Oct 29 2019 Petr Šplíchal <psplicha@redhat.com> - 0.14-2
- Include python3-setuptools in the BuildRequires
- Use info level to log problems with plugin import

* Tue Oct 22 2019 Petr Šplíchal <psplicha@redhat.com> - 0.14-1
- Include setup.py, use auto build/install, enable tests
- Fix 'did --test' when no config is present
- Update spec file for Python 3
- Update shebang to explicitly use python3
- Fix mixed tabs and spaces in docs/conf.py
- Goodbye Python 2! Thanks and have a good night ;-)
- Cleanup built docs directly
- Do not remove python's egg when doing the cleanup
- Document the custom plugin configuration
- A couple of custom plugins feature adjustments
- Support for custom plugin location [#160]
- Fix typo in the license classifier

* Tue Oct 01 2019 Petr Šplíchal <psplicha@redhat.com> - 0.13-1
- Support for the full file path config [#140]
- Add the 'last friday' command [#197]
- New plugin with basic confluence support [#199]
- Improve redmine documentation [#195]
- Add a new 'wip' option for gerrit [#194]
- Include project name in gerrit stats [#192]
- Fix the configuration examples for gerrit
- Simplify Pagure search for created issues
- Extended query for verified bugs [fix #189]
- Fix for reviewed gerrit changes [#188]
- Add gerrit work-in-progress changes [#187]
- Fix for gerrit log strings [#186]
- Improve gerrit search limit [#185]
- Document API key auth for bugzilla [fix #180]
- Mock bugzilla module to fix generating docs
- Update feedparser requires
- Fix for gerrit plugin typo [#179]

* Thu Dec 20 2018 Petr Šplíchal <psplicha@redhat.com> 0.12-1
- Add missing redmine dependency [fix #177]
- Fix GitLab plugin's ssl_verify option [fix #168]
- Document GitLab access token scope
- Merge ssl_verify support for Jira [#169]
- Merge support for Trello commented cards [#170]
- Fix commented cards title, improve the test suite
- Add a simple test for completed tasks, update auth
- Merge support for completed Google tasks [#173]
- Merge fix for the Google dependencies [#166]
- Document additional google dependencies
- Adding support for Google tasks
- Add commentCard to trello DEFAULT_FILTERS
- Allow to set 'ssl_verify' config for jira plugin
- Support 'creator' in bugzilla plugin [fix #167]
- Give a nice error when user not found [fix #159]
- Fix jira basic authentication [fix #163]
- Fix long_description in setup.py
- Update pip installation instructions
- Update the example config with recent plugins
- Describe in more detail how the tool works
- Silently ignore non-git directories [fix #143]
- Separate arguments preparation, add test coverage
- New option --test to run a simple smoke test
- Remove python2-gssapi from Requires
- Make REQUESTS_CA_BUNDLE example copy-paste-able
- Merge fix for the gitlab --since issue [fix #156]
- Remove gssapi dependency from the main cli module
- Quick start section, update install instructions
- Simplify setup.py, update requires
- Fix --since issue in gitlab plugin

* Mon Nov 26 2018 Petr Šplíchal <psplicha@redhat.com> 0.11-1
- Validate plugin types in config [fix #148]
- Use email for searching Jira issues [fix #122]
- Handle authentication errors in the Jira plugin
- Update shebang to explicitly use python2
- Add a new section Questions to docs [fix #155]
- Raise error on unsuccessful request [fix #154]
- New plugin for Pagure stats [fix #153]
- Use requests-gssapi for Jira stats
- Fix problems with the Sentry plugin
- Merge configurable ssl verify for gitlab [#136]
- Merge the improved gitlab search [#137]
- Merge the new redmine plugin [#135]
- Some minor adjustments for the redmine plugin
- GitHub stats about reviewed PRs [#127]
- Remove zero-fill from Jira issues [fix #149]
- Add oauth2client to docs requirements [fix #152]
- Adjust until limit of the sentry plugin [fix #151]
- Update test data for the sentry & google plugins
- Update Python macros to new packaging standards
- Port to python-gssapi
- Fixed issue with failing tests
- Remove the idonethis plugin
- Merge the new sentry plugin
- Add basic Redmine support
- Add basic GitLab support
- Add search for subscribed bugs
- Add did.spec to MANIFEST.in
- Merge fix for bugs patched when created [#109]
- Merge the new Bugzilla query syntax [#111]
- Fetch only needed stats during GitHub testing
- Merge support for pull request separation [#114]
- Show month name / week number by default [#106]

* Wed Jan 11 2017 Martin Frodl <mfrodl@redhat.com> 0.10-1
- New plugin for Google Apps
- Document how to generate documentation locally
- Mock C modules while building documentation
- Make all make versions happy
- Add requirements.txt to fix docs building
- Properly handle GitHub issues with Unicode names
- Add login key to github section in example config
- Update install docs with fresh Fedora instructions
- Update coveralls links in README
- List install dependencies for Debian-based systems
- Use another Trac instance in plugin test
- Move kerberos to extra requires

* Mon Apr 04 2016 Petr Šplíchal <psplicha@redhat.com> 0.9-1
- New plugins supported: Trello, bit.ly, idonethis
- Support 'did yesterday' for yesterday's updates
- Ignore comment updates without author specified
- User does not have to be assignee to close a bug
- Create vim tags using the 'make tags' target
- Use option prefix also for git, header and footer
- Extend the test coverage for cli, base and utils
- Rename DID_CONFIG to DID_DIR to match the content
- Improve error handling, especially config errors
- Migrate option parsing from optparse to argparse
- Configurable support for showing bug resolutions
- Support --conf as abbreviation for --config
- Initial set of tests for the trac plugin
- Improve readability of gerrit by using review number
- Improve closed bugs stats, add test case [fix #45]
- Add statistics of closed bugs for bugzilla plugin

* Wed Sep 23 2015 Petr Šplíchal <psplicha@redhat.com> 0.8-1
- Give warning for git repository problems [fix #41]
- Add example with config dir set to: ~/.config/did/
- Support for basic authentication in jira plugin
- Support config profiles (new option --config)
- Generate coverage annotations for 'make coverage'
- Support aliases in config sections, improves #36
- The first draft of the github plugin [fix #42]
- Support custom email/login aliases [fix #36]
- Include detailed description for general options
- Properly check email in gerrit messages [fix #34]
- Correctly handle invalid arguments [fix #33]
- Do not include the whole docs dir in the tarball
- Properly document how email addresses are handled
- Use wheels for python packaging (no source dist)
- Include Python package building stuff in Makefile

* Fri Sep 18 2015 Petr Šplíchal <psplicha@redhat.com> 0.7-1
- Refer Travis CI and Coveralls in contribute docs
- Remove version from the documentation completely
- Unshallow the git repo as it is used for testing
- Ignore errors about non-existent bugzilla emails
- Better handle xmlrpclib errors during bug search
- Document bugzilla plugin stats in more detail
- Bugzilla test suite adjustments (split, asserts)
- Log kerberos error as a debug message
- Decode command line arguments from utf-8
- Filter returned bugs by email or name
- Moving bug from NEW to ASSIGNED is not returning
- Improve fixed bugs detection in bugzilla plugin
- Allow stats name detection from multiline docs
- Do not run 'make clean' in the pre-commit hook
- Support fetching large queries in jira plugin
- Document stats order specification in config

* Fri Sep 11 2015 Petr Šplíchal <psplicha@redhat.com> 0.6-1
- Provide a couple of real-life examples in docs
- Convert plugin order list into table
- Update welcome page and module documentation
- Handle invalid dates, paths and urls
- Consider ticket description change as update
- Check free command line arguments for typos
- Include example config in docs, adjust man page
- Fix the --debug option, prevent logger duplication
- Correctly handle missing config file
- Move Options.time_period() to Date.period()
- Update source url, add python-bugzilla to requires
- Move stats classes into a separate module
- Completely remove get_color_mode/set_color_mode
- Adjust utils.pluralize() to take a single argument
- Adjust commit-msg hook to handle comments
- Move command line code to the did.cli module

* Wed Sep 09 2015 Petr Šplíchal <psplicha@redhat.com> 0.5-1
- New tests for command line script, bugzilla, git
- Update README with synopsis and today's example
- Clean up the Makefile, remove obsoleted stuff
- Document general command line options in overview
- Extend contribute doc with Introduction & Makefile
- Update and simplify git commit hooks
- Use config directory instead of a single file
- New Makefile targets: test, smoke, coverage, docs
- Add mr.bob template to generate new default plugin
- Enable package 'extras' (dependencies) install
- Do not ignore sphinx dirs _static and _templates
- Move script, modules & tests out of the source dir

* Sun Sep 06 2015 Petr Šplíchal <psplicha@redhat.com> 0.4-1
- What did you do last week, month, year? (did rename)
- Plugins: bugzilla, rt, gerrit, jira, wiki, nitrate
- Separate the install/contribute documentation
- Correctly handle config as utf8, email splitting
- The Big Documentation Cleanup, hooks to examples
- Allow parsing config file directly from string
- Allow config location override, read config once
- Move docs to sphinx, githooks, rpm build fix
- An initial cut at creating a docker container
- Refactor plugin/stats architecture
- Use Travis CI, add initial tests
- Move README, add code coverage and badges

* Thu Apr 23 2015 Petr Šplíchal <psplicha@redhat.com> 0.3-1
- Update README with PIP and test information
- Enable travis-ci and some tests
- A couple of adjustments after the nitrate cleanup
- Remove nitrate dependency, adjust user handling

* Wed Apr 22 2015 Petr Šplíchal <psplicha@redhat.com> 0.2-1
- Incorporated package review feedback [BZ#1213739]
- Include essential gitignore patterns
- Handle custom stats as a plugin as well
- Handle header & footer as other plugins
- Plugin detection finalized including sort order
- Style cleanup and adjustments for plugin detection
- The first version of the plugin detection support

* Mon Apr 20 2015 Petr Šplíchal <psplicha@redhat.com> 0.1-0
- Initial packaging.
