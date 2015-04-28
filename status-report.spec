Name: status-report
Version: 0.4
Release: 1%{?dist}

Summary: Generate status report stats for selected date range
License: GPLv2+

URL: http://psss.fedorapeople.org/status-report/
Source0: http://psss.fedorapeople.org/status-report/download/%{name}-%{version}.tar.bz2

BuildArch: noarch
BuildRequires: python-devel
Requires: python-kerberos python-nitrate python-dateutil

%description
Comfortably generate status report stats (e.g. list of committed
changes) for given week, month, quarter, year or selected date
range. By default all available stats for this week are reported.

%prep
%setup -q

%build

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_mandir}/man1
mkdir -p %{buildroot}%{python_sitelib}/status_report
mkdir -p %{buildroot}%{python_sitelib}/status_report/plugins
install -pm 755 source/status-report %{buildroot}%{_bindir}
install -pm 644 source/status_report/*.py %{buildroot}%{python_sitelib}/status_report
install -pm 644 source/status_report/plugins/*.py %{buildroot}%{python_sitelib}/status_report/plugins
install -pm 644 docs/_build/man/*.1.gz %{buildroot}%{_mandir}/man1

%files
%{_mandir}/man1/*
%{_bindir}/status-report
%{python_sitelib}/*
%doc README.rst examples
%{!?_licensedir:%global license %%doc}
%license LICENSE

%changelog
* Sun Apr 26 2015 Chris Ward <cward@redhat.com> 0.4-1
- Snippet saving and reporting functionality added
- Refactor of Stat classes; don't fetch during __init__()
- Docker builds enabled [langdon@redhat.com]
- More tests!

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
