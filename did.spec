Name: did
Version: 0.7
Release: 1%{?dist}

Summary: What did you do last week, month, year?
License: GPLv2+

URL: https://github.com/psss/did
Source: https://github.com/psss/did/releases/download/%{version}/did-%{version}.tar.bz2

BuildArch: noarch
BuildRequires: python-devel
Requires: python-kerberos python-nitrate python-dateutil python-urllib2_kerberos python-bugzilla

%description
Comfortably gather status report data (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_mandir}/man1
mkdir -p %{buildroot}%{python_sitelib}/did
mkdir -p %{buildroot}%{python_sitelib}/did/plugins
install -pm 755 bin/did %{buildroot}%{_bindir}/did
install -pm 644 did/*.py %{buildroot}%{python_sitelib}/did
install -pm 644 did/plugins/*.py %{buildroot}%{python_sitelib}/did/plugins
install -pm 644 docs/*.1.gz %{buildroot}%{_mandir}/man1


%files
%{_mandir}/man1/*
%{_bindir}/did
%{python_sitelib}/*
%doc README.rst examples
%{!?_licensedir:%global license %%doc}
%license LICENSE

%changelog
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
