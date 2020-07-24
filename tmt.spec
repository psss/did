Name: tmt
Version: 0.19
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
Requires: git-core sshpass

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

%package provision-container
Summary: Container provisioner for the Test Management Tool
Obsoletes: tmt-container < 0.17
Requires: tmt == %{version}-%{release}
Requires: ansible podman

%description provision-container
Dependencies required to run tests in a container environment.

%package provision-virtual
Summary: Virtual machine provisioner for the Test Management Tool
Obsoletes: tmt-testcloud < 0.17
Requires: tmt == %{version}-%{release}
Requires: python%{python3_pkgversion}-testcloud >= 0.3.5
Requires: ansible openssh-clients rsync

%description provision-virtual
Dependencies required to run tests in a local virtual machine.

%package all
Summary: Extra dependencies for the Test Management Tool
Requires: tmt >= %{version}
Requires: tmt-provision-container >= %{version}
Requires: tmt-provision-virtual >= %{version}
Requires: python3-nitrate make
Recommends: vagrant

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

%{__python3} -m pytest -vv -m 'not web'


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
%exclude %{python3_sitelib}/%{name}/steps/provision/{,__pycache__/}{podman,testcloud}.*

%files provision-container
%{python3_sitelib}/%{name}/steps/provision/{,__pycache__/}podman.*

%files provision-virtual
%{python3_sitelib}/%{name}/steps/provision/{,__pycache__/}testcloud.*

%files all
%license LICENSE


%changelog
* Fri Jun 12 2020 Petr Šplíchal <psplicha@redhat.com> - 0.19-1
- Make the discover step a little bit more secure
- Improve basic and verbose output of tmt plan show
- Improve default plan handling and more [fix #287]
- Adjust the compose check retry in testcloud
- Retry Fedora compose check in testcloud [fix #275]
- Update development section and library example
- Support fetching beakerlib libraries in discover
- Add nitrate to the setup.py extra requires
- Add a workflow-tomorrow integration test example
- Add 'duration' into the test results specification

* Mon Jun 01 2020 Petr Šplíchal <psplicha@redhat.com> - 0.18-1
- Add virtual plans for supported provision methods
- Implement description in 'tmt plan show' as well
- Implement tmt run --remove to remove workdir
- Extend the login/step test to cover failed command
- Do not fail upon command fail in interactive mode
- Implement the internal tmt execute step method
- Move all prepare/install tests to tier level 3
- Merge the new manual test specification [#247]
- Merge the new L1 attribute 'recommend' [#265]
- Adjust the manual test specification and examples
- Implement 'recommend' for installing soft requires
- State explicitly that execution is finished
- Simplify beakerlib template, add test for init
- Manual test case specification and examples
- Implement exit codes, handle no tests [fix #246]
- Merge the interactive shell login command [#258]
- Adjust support for shortened 1MT image names
- New login command to provide a shell on guest
- Add support for shortened 1MT image names
- Add support for running tests without defined plan
- Ignore save() in the execute step unit test
- Update the default run example with fresh output
- Show kernel version only in verbose mode

* Sat May 23 2020 Petr Šplíchal <psplicha@redhat.com> - 0.17-1
- Use emulator_path instead of hard-coded qemu path
- Improve a bit the --force option description
- Use consistent naming for provision subpackages
- Add 'mock' to extra requires (needed to make docs)
- Move podman and testcloud plugins into subpackages
- Enable epel for packit build & testing farm
- Move vagrant from requires to recommends (tmt-all)

* Mon May 18 2020 Petr Šplíchal <psplicha@redhat.com> - 0.16-1
- Merge the fix and test for run --force [#245]
- Merge the improved display report [#241]
- Adjust the display report plugin verbose output
- Adjust general plan linking and component check
- Clean up the run workdir if --force provided
- More verbose modes for report --how display
- Link plans, handle missing components in export
- Import and listify of contact
- Disable Tier 3 tests by default (need bare metal)
- Move Tier 0 tests into a separate directory
- Merge the new 1minutetip provision plugin [#225]
- Adjust the 1minutetip provision plugin
- Add support for tmt run --after and --before (#237)
- Support string in test component, require and tag (#233)
- Add support for installing local rpm packages
- Add 1minutetip provision plugin
- Implement tmt run --since, --until and --skip (#236)
- Merge pull request #234 from psss/testcloud-aliases
- Update the last run id at the very end of run
- Support short Fedora compose aliases in testcloud
- Convert the finish step into dynamic plugins
- Convert the report step into dynamic plugins
- Convert the execute step into dynamic plugins
- Escape package names during installation
- Deduplicate inherited keys in test import [fix #8]

* Wed Apr 29 2020 Petr Šplíchal <psplicha@redhat.com> - 0.15-1
- Implement executing the last run using --last
- Adjust support for modifying plan templates
- Add a way how to edit values in a new template
- Explicitly mention supported distros in the docs
- Convert provision/prepare into dynamic plugins
- Describe difference between --verbose and --debug
- Support fmf name references in docs, update spec
- Support multiple verbose/debug levels [fix #191]
- Remove forgotten 'Core' section from stories
- Implement Plugin.show() for a full dynamic support
- Improve the workdir handling in the Common class

* Thu Apr 16 2020 Petr Šplíchal <psplicha@redhat.com> - 0.14-1
- Workaround yaml key sorting on rhel-8 [fix #207]
- Fix test discovery from the execute step scripts
- Merge discover step documentation and fixes [#204]
- Document the discover step, fix issues, add tests
- Simplify the minimal example, adjust tests
- Move fmf_id() to Node class, minor adjustments
- Allow to print fmf identifier in tmt tests show
- Merge manual tests story and examples [#198]
- Add a story and examples describing manual tests
- Sync more extra-* attributes when exporting [#199]
- Enable checks for essential test attributes
- Handle require in Dicovery
- Store imported metadata in a sane order [fix #86]
- Enable Python 3.8 in Travis, update classifiers
- Add missing 'require' attribute to the Test class
- Fix long environment for run.sh [fix #126]
- Merge dynamic plugins and wake up support [#186]
- Implement dynamic plugins and options [fix #135]
- Suggest using 'tmt init' when metadata not found
- Merge improved import of tier from tags [#187]
- Adjust tier import from test case tags
- Merge tmt test export --nitrate --create [#185]
- Adjust suppport for creating new nitrate testcases
- Allow creation of nitrate cases when exporting
- Create tier attribute from multiple Tier tags
- Fix run.sh to work with RHEL/CentOS 7 as well
- Implement wake up for Run, Step and Discover

* Wed Apr 01 2020 Petr Šplíchal <psplicha@redhat.com> - 0.13-1
- Merge the improved test import checks [#179]
- Adjust checks for missing metadata
- Add checks for missing metadata.
- Implement public_git_url() for git url conversion
- Define required attributes and duration default

* Wed Mar 25 2020 Petr Šplíchal <psplicha@redhat.com> - 0.12-1
- Import the testcloud module when needed [fix #175]
- Update implementation coverage of stories & spec
- Discover only enabled tests [fix #170]
- Correctly handle missing nitrate module or config
- Use raw string for regular expression search

* Mon Mar 23 2020 Petr Šplíchal <psplicha@redhat.com> - 0.11-1
- Merge default images for podman/testcloud [#169]
- Do not export empty environment to run.sh
- Merge vagrant check for running connection [#156]
- Adjust vagrant check for running connection
- Merge test export into nitrate [#118]
- Adjust 'tmt test export --nitrate' implementation
- Use fedora as a default image for podman/testcloud
- Move testcloud back to the extra requires
- Always copy directory tree to the workdir
- Add an example with test and plan in a single file
- Do not run tests with an empty environment
- Check for non-zero status upon yaml syntax errors
- Export test cases to nitrate
- Merge test import using testinfo.desc [#160]
- Adjust test import using testinfo.desc
- Use testinfo.desc as source of metadata
- Add environment support to the discover step (#145)
- Add a new story describing user and system config (#143)
- Check if connection is running in Vagrant Provision

* Wed Mar 11 2020 Petr Šplíchal <psplicha@redhat.com> - 0.10-1
- Merge fixed environment support in run.sh [#99]
- Add container and testcloud to tmt-all requires (#157)
- Rename dict_to_shell() to better match content
- Make path mandatory in run.sh.
- Handle execution better in run.sh
- Implement --env for testcloud provisioner
- Merge run --environment support for podman [#132]
- Fix container destroy, plus some minor adjustments
- Use cache 'unsafe' for testcloud (#150)
- Add --env option and support in podman provisioner
- Warn about missing metadata tree before importing
- Move testcloud to base requires, update README (#153)
- Destroy container in finish only if there is any
- Merge tmt test import --nitrate --disabled [#146]
- Adjust the disabled test import implementation
- Add an overview of classes (where are we heading)
- Import non-disabled tests
- Add a 'Provision Options' section, update coverage
- Support selecting objects under the current folder
- Add a link to details about fmf inheritance
- Move requirements under the Install section
- Mock testcloud modules to successfully build docs
- Include examples of plan inheritance [fix #127]
- Update implementation coverage for cli stories
- Add testcloud provisioner (#134)
- Merge the new story for 'tmt run --latest' [#136]
- Move run --latest story under run, fix code block
- Fix invalid variable name in the convert example
- Use 'skip' instead of 'without', simplify default
- Add rerun cli shortcut
- Make sure we run finish always
- Update the docs making '--name=' necessary (#138)
- Clarify environment priority, fix release typo
- Add environment specification
- Remove copr build job from packit (not necessary)
- Use the 'extra-summary' in the output as well
- Use 'nitrate' consistently for tcms-related stuff
- Prefix all non-specification keys [fix #120]
- Show a nice error for an invalid yaml [fix #121]
- Move container plan to common provision examples
- Remove tmt-all dependency on vagrant-libvirt
- Do not use red for import info messages [fix #125]
- Show a nice error for weird Makefiles [fix #108]

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
