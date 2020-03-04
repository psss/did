Name: tmt
Version: 0.9
Release: 1%{?dist}

Summary: Test Management Tool
License: MIT
BuildArch: noarch

URL: https://github.com/psss/tmt
Source0: https://github.com/psss/tmt/releases/download/%{version}/tmt-%{version}.tar.gz

# Depending on the distro, we set some defaults.
# Note that the bcond macros are named for the CLI option they create.
# "%%bcond_without" means "ENABLE by default and create a --without option"

# Fedora or RHEL 8+
%if 0%{?fedora} || 0%{?rhel} > 7
%bcond_with oldreqs
%bcond_with englocale
%else
# The automatic runtime dependency generator doesn't exist yet
%bcond_without oldreqs
# The C.UTF-8 locale doesn't exist, Python defaults to C (ASCII)
%bcond_without englocale
%endif

# Main tmt package requires the Python module
Requires: python%{python3_pkgversion}-%{name} == %{version}-%{release}
Requires: git-core

%description
The tmt Python module and command line tool implement the test
metadata specification (L1 and L2) and allows easy test execution.
This package contains the command line tool.

%?python_enable_dependency_generator


%package -n     python%{python3_pkgversion}-%{name}
Summary:        Python library for the %{summary}
BuildRequires: python%{python3_pkgversion}-devel
BuildRequires: python%{python3_pkgversion}-setuptools
BuildRequires: python%{python3_pkgversion}-pytest
BuildRequires: python%{python3_pkgversion}-click
BuildRequires: python%{python3_pkgversion}-fmf
BuildRequires: python%{python3_pkgversion}-mock
BuildRequires: python%{python3_pkgversion}-requests
BuildRequires: python%{python3_pkgversion}-testcloud
%{?python_provide:%python_provide python%{python3_pkgversion}-%{name}}
%if %{with oldreqs}
Requires:       python%{python3_pkgversion}-PyYAML
%endif

%description -n python%{python3_pkgversion}-%{name}
The tmt Python module and command line tool implement the test
metadata specification (L1 and L2) and allows easy test execution.
This package contains the Python 3 module.

%package container
Summary: Container provisioner for the Test Management Tool
Requires: tmt == %{version}-%{release}
Requires: ansible podman

%description container
All dependencies of the Test Management Tool required to run tests
in a container environment.

%package testcloud
Summary: Libvirt (via testcloud) provisioner for the Test Management Tool
Requires: tmt == %{version}-%{release}
Requires: ansible python%{python3_pkgversion}-testcloud openssh-clients rsync

%description testcloud
All dependencies of the Test Management Tool required to run tests
in a libvirt environment provisioned using testcloud.

%package all
Summary: Extra dependencies for the Test Management Tool
Requires: tmt == %{version}-%{release}
Requires: vagrant python3-nitrate

%description all
All extra dependencies of the Test Management Tool. Install this
package to have all available plugins ready for testing.


%prep
%setup -q


%build
%if %{with englocale}
export LANG=en_US.utf-8
%endif

%py3_build


%install
%if %{with englocale}
export LANG=en_US.utf-8
%endif

%py3_install

mkdir -p %{buildroot}%{_mandir}/man1
mkdir -p %{buildroot}/etc/bash_completion.d/
install -pm 644 tmt.1* %{buildroot}%{_mandir}/man1
install -pm 644 bin/complete %{buildroot}/etc/bash_completion.d/tmt


%check
%if %{with englocale}
export LANG=en_US.utf-8
%endif

%{__python3} -m pytest -vv


%{!?_licensedir:%global license %%doc}

%files
%{_mandir}/man1/*
%{_bindir}/%{name}
%doc README.rst examples
%license LICENSE
/etc/bash_completion.d/tmt


%files -n python%{python3_pkgversion}-%{name}
%{python3_sitelib}/%{name}/
%{python3_sitelib}/%{name}-*.egg-info/
%license LICENSE


%files container
%license LICENSE


%files testcloud
%license LICENSE


%files all
%license LICENSE


%changelog
* Mon Feb 24 2020 Petr Šplíchal <psplicha@redhat.com> - 0.9-1
- Rename the 'test convert' command to 'test import'
- Include 'path' when importing virtual test cases
- Extract test script from Makefile during convert
- Do not import 'fmf-export' tag from nitrate [#119]
- Merge the improved component import [#115]
- Several adjustments to the component import
- Merge the improved requires parsing [#113]
- Fix parsing multiple requires from Makefile
- Fail nicely if executed without provision (#112)
- Make sure the copr command is available in dnf
- Fix handling defaults for options, adjust wording
- Read 'components' from nitrate when converting
- Read requires as list when converting tests
- Make it possible to pass script on cmdline
- Mention libvirt and rsync in Fedora 30 workaround
- Move podman image check and pull under go()
- Simple destroy implementation for podman provision
- Add Fedora 30 installation instructions [fix #105]
- Merge podman support for the provision step [#106]
- Several adjustments to the podman implementation
- Fix _prepare_shell in podman provisioner
- Add podman provisioner
- Update the test case relevancy specification (#102)
- Move copy_from_guest to provision/base.py (#75)
- Several minor adjustments to the restraint story
- Add user story for restraint
- Merge different summaries for subpackages [#97]
- Remove macro from the tmt-all subpackage summary
- Add different summaries for sub-packages
- Mention 'fmf-export' tag in the test export story
- Merge optional PURPOSE in test convert [#89]
- Handle missing duration or nitrate case in convert
- Add support for wrap='auto' in utils.format()
- Use local fmf repository for the basic plan (#94)
- Merge test import documentation updates [#90]
- Merge tag, status, pepa & hardware for test import
- Several test import adjustments related to #91
- Fix deduplication bug when converting tests
- Read more attributes from nitrate when converting
- Update examples doc for converting tests
- Update execute step examples for shell
- Simplify packit configuration using 'fedora-all' (#88)
- Optional attributes when converting.
- Update execute and report step specification
- Add spec for results.yaml and report.yaml (#66)
- Add a story for exporting tests into nitrate (#83)
- Add the 'require' attribute into the L1 Metadata
- Update the Metadata Specification link in README
- Improve 'tmt test convert' command implementation

* Wed Jan 15 2020 Petr Šplíchal <psplicha@redhat.com> - 0.8-1
- Do not create bash completion script during build
- Require the same version, fix changelog entry
- Create fmf for each tcms case when converting. (#78)

* Tue Jan 14 2020 Petr Šplíchal <psplicha@redhat.com> - 0.7-1
- Make the package build for epel7 and epel8
- Implement test discover from execute shell script
- Disable /plan/helps for running in cruncher (#74)
- Do not fail ansible execution on 'stty cols' error
- Use a list for storing converted requires
- Add Requires to main.fmf when converting tests (#65)
- Fix command debug output to join tuples as well. (#77)
- Set 80 chars for ansible-playbook on localhost
- Use tmt to init tree, extra folder for playbooks
- Fix log and error handling in execute
- Fail in run.sh if there are Missing tests.
- Use sudo in prepare step to allow local execution
- Fix run_vagrant() to work with shell=True
- Use tmt init --template, not --mini|--base|--full (#69)
- Add a simple local provision plan to examples
- Simplify step selection test, simple local example
- Fix conflicting options, revert copr config
- Add `--guest` support for the provision step
- Depend on git-core and not the full git package (#64)
- Use shell=True as a default in utils' run()
- Put quotes in `pip install .[*]` in README (#67)
- Use parent run context to check for enabled steps
- Improve the enabled steps implementation
- Add 'mock' to the extra test requires [fix #63]
- Add a new story for developing upgrade tests
- Update fedora targets for packit
- Add vagrant to BuildRequires (needed to run tests)
- Add stories for connecting to a provisioned box
- Separate the provision step into multiple stories
- Fix provision tests to work with older mock (#51)
- Install the latest mock module for testing
- Default to vagrant provision, use the tree root
- Update documentation coverage links
- Move new docs to examples, adjust style & content
- Add prepare functionality to local provision
- Import examples from @psss's talk
- Add an argument to ProvisionBase.copy_from_guest (#41)
- Remove unused imports, fix crash, shell prepare
- Initial prepare and finish steps implementation
- Document the vagrant-rsync-back plugin workaround
- Fix beakerlib execution, show overall results
- Better execute with logs and better run.sh
- Implement 'tmt init --base' with working examples
- Add git to the main package requires
- Add tmt & python3-nitrate to the tmt-all requires
- Create subpackage 'tmt-all' with all dependencies
- Use package_data to package the test runner
- Apply requested file mode in create_file()
- Run tmt tests local by default, fix provision show
- Implement image selection using provision --image
- Do not re-raise tmt exceptions in debug mode
- Package the runner, dry mode in Common.run()
- Support multiline output in common display methods
- Enable command line filtering in discover.shell
- Default discover method has to be 'shell'
- Fix Common.run() to capture all output, log all
- Fix broken test/plan/story create, add some tests
- Better config handling in ProvisionVagrant.
- Implement 'sync-back' and simple VagrantProvision.

* Mon Nov 04 2019 Petr Šplíchal <psplicha@redhat.com> - 0.6-1
- List all python packages in the setup.py
- Initial implementation of the execute step
- Vagrant Provider output and provider handling
- Relay API methods to instances in provision
- Simple localhost provisioner (#28)
- Implement shell discover, add a simple example
- Fix test path, discover in go(), adjust example
- Add run.sh for running the tests on guest
- Add default config for libvirt to use QEMU session

* Tue Oct 29 2019 Petr Šplíchal <psplicha@redhat.com> - 0.5-1
- Implement common --filter and --condition options
- Store step data during save()
- Common logging methods, improve run() output
- Implement common options and parent checking
- Sync the whole plan workdir to the guest
- Fix inheritance and enable --verbose mode.
- Rename the main metadata tree option to --root
- Adjust tests to skip provision, fix raw strings
- Move example Vagrantfiles to examples
- Implement ProvisionVagrant (#20)
- Implement tests.yaml creation in discover
- Implement 'tmt test export' with yaml support
- Support checking parent options, fix plan show -v
- Implement common methods status(), read(), write()
- Implement run() to easily execute in the workdir
- Implement DiscoverPlugin class, require step names
- Move workdir handling into the Common class
- Common class & filtering tests/plans for execution
- Improve step handling, remove global variables
- Fix 'tmt init --full' in a clean directory
- Better handle defaults and command line options
- Do not run systemd plan as it fetches remote repo
- Add documentation generated files to gitignore
- Get rid of the test attribute inconsistencies
- Fix various issues in localhost provisioner skeleton
- Update discover step story with example output
- Add an example of a shell discover step
- Add a simple smoke test story
- Add base class for provisioner
- Initial implementation of the discover step
- Allow creating tmt tree under an existing one
- Support multiple configs in Step.show()
- Support and document optional dependencies install
- Add an example of multiple configs
- Convert step data to list, add execute check
- Add --how option to provision command
- Move step classes into separate directories
- Implement class Run with workdir support
- Add a workdir structure example
- Separate metadata tree for L2 metadata examples
- Add stories covering the Metadata Specification
- Enable bash completion feature

* Thu Oct 17 2019 Petr Šplíchal <psplicha@redhat.com> - 0.4-1
- Add tests for 'tmt init', allow overwritting
- Use plural commands to prevent confusion [fix #10]
- Add a link to Packit & Testing Farm documentation
- Add a simple develop section to the readme
- Split cli stories into multiple files
- Cleanup convert example, simplify story example
- Implement initialization with creating examples
- Implement 'tmt {test,plan,story} show --verbose'
- Implement 'tmt story create', add basic templates
- Implement 'tmt plan create' plus initial templates
- Add a new story for creating plans (enable CI)
- Add basic rpm installation stories
- Show test steps summary in plan show if provided
- Add a Release Test Team installation tests example
- Suggest git-like moving forward in tasks
- Fix step names in 'tmt plan show' output
- Update documentation overview with latest changes
- Add story introduction, cleanup generated files
- Generate documentation for user stories
- Use raw string to prevent invalid escape sequence
- Test Management Tool, it's not metadata only
- Add a story for core option --debug
- Add a story for the mock shortcut [fix #5, fix #6]
- Add a story for core option --format
- Propose a dream for hands-free debugging
- Rename remaining testset occurences to plan
- Implement 'tmt plan lint' with initial checks

* Thu Oct 10 2019 Petr Šplíchal <psplicha@redhat.com> - 0.3-1
- Fix uncovered story filter logic, show total
- Rename testsets to plans, simplify playbooks
- Fix basic testset repo, install dependencies
- Implement 'tmt init', add the corresponding story
- Show overview of available tests, plans, stories
- Implement 'tmt story coverage', update coverage
- Implement 'tmt story --covered / --uncovered'
- Rename testsest to plan to avoid common prefix

* Wed Oct 09 2019 Petr Šplíchal <psplicha@redhat.com> - 0.2-1
- Enable Packit building and Testing Farm testing
- Provide one-letter versions for select options
- Implement 'tmt run --all' to run all test steps
- Support command abbreviation, add related stories
- Add the Quick Start Guide story to documention
- Add coverage options to tmt story ls and show
- Initialize metadata tree only when accessed
- Remove show functionality from the 'run' command
- Implement 'tmt test create' with basic templates
- Implement 'tmt test lint' with some basic checks
- Add user stories for core options and attributes
- Implement 'tmt story show', couple of adjustments
- Prevent alphabetical sorting of commands in help
- Move unit tests into a separate directory
- Align examples with the latest specification
- Implement 'tmt show' for test and testset
- Implement ls for test, testset and story commands
- Add 'tmt test create' command to user stories
- Add an initial set of basic tests
- Update cli user stories, add api & docs stories
- Add a couple of dreams for the bright future :-)

* Mon Sep 30 2019 Petr Šplíchal <psplicha@redhat.com> - 0.1-1
- Initial packaging
