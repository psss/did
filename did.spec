Name: did
Version: 0.4
Release: 1%{?dist}

Summary: What did you do last week, month, year?
License: GPLv2+

URL: https://github.com/psss/did
Source0: http://psss.fedorapeople.org/did/download/%{name}-%{version}.tar.bz2

BuildArch: noarch
BuildRequires: python-devel
Requires: python-kerberos python-nitrate python-dateutil python-urllib2_kerberos

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
