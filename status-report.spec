Name: status-report
Version: 0.1
Release: 0%{?dist}

Summary: Generate status report stats for selected date range
Group: Applications/Productivity
License: GPLv2

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
install -pm 644 docs/*.1.gz %{buildroot}%{_mandir}/man1

%files
%{_mandir}/man1/*
%{_bindir}/status-report
%{python_sitelib}/*
%doc LICENSE README examples

%changelog
* Mon Apr 20 2015 Petr Šplíchal <psplicha@redhat.com> 0.1-0
- Initial packaging.
