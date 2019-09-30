Name: tmt
Version: 0.1
Release: 1%{?dist}

Summary: Test Metadata Tool
License: MIT
BuildArch: noarch

URL: https://github.com/psss/tmt
Source: https://github.com/psss/tmt/releases/download/%{version}/tmt-%{version}.tar.gz

# Depending on the distro, we set some defaults.
# Note that the bcond macros are named for the CLI option they create.
# "%%bcond_without" means "ENABLE by default and create a --without option"

# Fedora 30+ or RHEL 8+ (py3 executable, py3 subpackage, auto build requires)
%if 0%{?fedora} > 29 || 0%{?rhel} > 7
%bcond_with python2
%bcond_without python3
%bcond_with py2executable
%bcond_with oldreqs

# Older RHEL (py2 executable, py2 subpackage, manual build requires)
%else
%if 0%{?rhel}
%bcond_without python2
%bcond_with python3
%bcond_without py2executable
%bcond_without oldreqs

# Older Fedora (py3 executable, py3 & py2 subpackage, auto build requires)
%else
%bcond_without python2
%bcond_without python3
%bcond_with py2executable
%bcond_with oldreqs
%endif
%endif

# Main tmt package requires corresponding python module
%if %{with py2executable}
Requires: python2-%{name} == %{version}-%{release}
%else
Requires: python%{python3_pkgversion}-%{name} == %{version}-%{release}
%endif

%description
The tmt Python module and command line tool implement the test
metadata specification (L1 and L2) and allows easy test execution.
This package contains the command line tool.

%?python_enable_dependency_generator


# Python 2
%if %{with python2}
%package -n     python2-%{name}
Summary:        %{summary}
BuildRequires: python2-devel
BuildRequires: python2-setuptools
%if %{with oldreqs}
BuildRequires: pytest
BuildRequires: python2-fmf
BuildRequires: python2-click
%else
BuildRequires: python2dist(pytest)
BuildRequires: python2dist(pyyaml)
BuildRequires: python2dist(click)
BuildRequires: python2dist(fmf)
%endif
%{?python_provide:%python_provide python2-%{name}}
%if %{with oldreqs}
%endif

%description -n python2-%{name}
The tmt Python module and command line tool implement the test
metadata specification (L1 and L2) and allows easy test execution.
This package contains the Python 2 module.
%endif


# Python 3
%if %{with python3}
%package -n     python%{python3_pkgversion}-%{name}
Summary:        %{summary}
BuildRequires: python%{python3_pkgversion}-devel
BuildRequires: python%{python3_pkgversion}-setuptools
BuildRequires: python%{python3_pkgversion}-pytest
BuildRequires: python%{python3_pkgversion}-click
BuildRequires: python%{python3_pkgversion}-fmf
%{?python_provide:%python_provide python%{python3_pkgversion}-%{name}}
%if %{with oldreqs}
Requires:       python%{python3_pkgversion}-PyYAML
%endif

%description -n python%{python3_pkgversion}-%{name}
The tmt Python module and command line tool implement the test
metadata specification (L1 and L2) and allows easy test execution.
This package contains the Python 3 module.
%endif


%prep
%setup -q


%build
%if 0%{?fedora} < 30 || 0%{?rhel}
export LANG=en_US.utf-8 # for Python <= 3.6 and EPEL <= 7, but harmless
%endif

%if %{with python2}
%py2_build
%endif
%if %{with python3}
%py3_build
%endif


%install
%if 0%{?fedora} < 30 || 0%{?rhel}
export LANG=en_US.utf-8
%endif

%if %{with python2}
%py2_install
%endif

%if %{with python3}
%py3_install
%endif

%if %{with py2executable} && %{with python3}
rm -f %{buildroot}%{_bindir}/*
%py2_install
%endif

mkdir -p %{buildroot}%{_mandir}/man1
install -pm 644 tmt.1* %{buildroot}%{_mandir}/man1


%check
export LANG=en_US.utf-8

%if %{with python2}
%{__python2} -m pytest -vv
%endif

%if %{with python3}
%{__python3} -m pytest -vv
%endif


%{!?_licensedir:%global license %%doc}


%files
%{_mandir}/man1/*
%{_bindir}/%{name}
%doc README.rst examples
%license LICENSE

%if %{with python2}
%files -n python2-%{name}
%{python2_sitelib}/%{name}/
%{python2_sitelib}/%{name}-*.egg-info
%license LICENSE
%endif

%if %{with python3}
%files -n python%{python3_pkgversion}-%{name}
%{python3_sitelib}/%{name}/
%{python3_sitelib}/%{name}-*.egg-info
%license LICENSE
%endif


%changelog
* Thu Sep 05 2019 Petr Šplíchal <psplicha@redhat.com> - 0.1-1
- Initial packaging.
