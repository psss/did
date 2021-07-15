Name: tmt
Version: 1.6.0
Release: 1%{?dist}

Summary: Test Management Tool
License: MIT
BuildArch: noarch
%{?kernel_arches:ExclusiveArch: %{kernel_arches} noarch}

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
Requires: git-core rsync sshpass

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
BuildRequires: python%{python3_pkgversion}-markdown
BuildRequires: python%{python3_pkgversion}-junit_xml
# Required for tests
BuildRequires: rsync
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
Requires: python%{python3_pkgversion}-testcloud >= 0.6.0
Requires: ansible openssh-clients

%description provision-virtual
Dependencies required to run tests in a local virtual machine.

%package test-convert
Summary: Test import and export dependencies
Requires: make python3-nitrate python3-html2text python3-markdown

%description test-convert
Additional dependencies needed for test metadata import and export.

%package report-html
Summary: Report plugin with support for generating web pages
Requires: python3-jinja2

%description report-html
Generate test results in the html format. Quickly review test
output thanks to direct links to output logs.

%package report-junit
Summary: Report plugin with support for generating JUnit output file
Requires: python3-junit_xml

%description report-junit
Generate test results in the JUnit format.

%package all
Summary: Extra dependencies for the Test Management Tool
Requires: tmt >= %{version}
Requires: tmt-provision-container >= %{version}
Requires: tmt-provision-virtual >= %{version}
Requires: tmt-test-convert >= %{version}
Requires: tmt-report-html >= %{version}
Requires: tmt-report-junit >= %{version}

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

%{__python3} -m pytest -vv -m 'not web' --ignore=tests/integration


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
%exclude %{python3_sitelib}/%{name}/steps/report/{,__pycache__/}html.*
%exclude %{python3_sitelib}/%{name}/steps/report/{,__pycache__/}junit.*

%files provision-container
%{python3_sitelib}/%{name}/steps/provision/{,__pycache__/}podman.*

%files provision-virtual
%{python3_sitelib}/%{name}/steps/provision/{,__pycache__/}testcloud.*

%files report-html
%{python3_sitelib}/%{name}/steps/report/{,__pycache__/}html.*

%files report-junit
%{python3_sitelib}/%{name}/steps/report/{,__pycache__/}junit.*

%files test-convert
%license LICENSE

%files all
%license LICENSE


%changelog
* Wed Jun 02 2021 Petr Šplíchal <psplicha@redhat.com> - 1.6.0-1
- Adjust the new plugin documentation
- Add plugin examples and documentation
- Ensure that the discover git reference is a string
- Report plugin for JUnit output
- Fix issue when raising error for NoneType
- Print better error when nitrate testcase not found.
- Use `count=True` for multiple flag options
- Add option to explicitly use default plan
- Adjust debuginfo installation, add test coverage
- Use debuginfo-install for installing debuginfos
- Update the documentation based on refactoring
- Implement tmt story lint
- Refactor Node class to Core
- Correctly handle spaces in file/directory names
- Hand over plan environment during local execution
- Do not execute manual test cases
- Fix option handling for plugins with common prefix
- Propagate options to guests based on the step
- Support fetching libraries from a local directory
- Add a simple example of a test written in ansible
- Pass environment variables to ansible (local)
- Pass environment variables to ansible (virtual)
- Adjust warning for extra lines in Makefile targets
- Add test import warning for run and build targets
- Enable a few more pre-commit hooks, sort imports
- Give a warning about the obsoleted minute plugin
- Clarify adjust dependency on explicit context
- Fix the EPEL installation instructions
- Adjust the new list options for the minute plugin
- New print method, used now in minute plugin
- Implement listing available minute images/flavors
- Update default option values for verbose and debug
- Avoid creating workdir on --help
- Do not keep run workdir during testing
- Clean up the code style, remove the vagrant plugin

* Fri Apr 30 2021 Petr Šplíchal <psplicha@redhat.com> - 1.5.0-1
- Enable and document `pre-commit` and `autopep8`
- Reorganize feature stories, fix title duplication
- Prepare/install story for package development.
- Add package preparation scenarios from Fedora CI
- Prepare/install story for released packages
- Add new stories related to package preparation
- Fix login not working for cloud images
- Work around a seccomp podman issue on centos-8
- Tag multihost tests during import from Makefile
- Adjust the simple test for ansible prepare
- Remove hardcoded ansible_python_interpreter=auto
- Fix lint and use it on the tmt repo itself
- Obsolete the minute provision plugin
- Update the documentation for contributors
- Do not assert installed packages for recommend
- Show link to the full debug log in the html report
- Implement tmt clean command
- Require a newer fmf which supports storing data
- Allow to specify port in provision.connect
- Surround classes and functions with 2 blank lines
- Fix order of imports, sort them alphabetically
- Update the provision step hardware specification
- Fix tmt plan lint for multiple configurations
- Add tmt status examples section
- Add a context adjust example for the prepare step
- Adjust the git suffix stripping for known forges
- Strip git suffix from pagure/gitlab/github repos
- Enable install plans for pull request testing
- Adjust the essential attributes description
- Document the essential class attributes
- Improve the prepare step documentation
- Correctly convert relevancy with the `!=` operator
- Print note in report.html if it exists
- Add note about error for beakerlib results
- Adjust progress bar for the internal executor
- Add test progress bar to non-verbose mode
- Adjust the attribute linting for tests
- Lint attribute names for test
- Human friendly names for VMs

* Tue Apr 06 2021 Petr Šplíchal <psplicha@redhat.com> - 1.4.0-1
- Create a copy of nitrate testplans for iteration
- Check the rsync as the first preparation step
- Use an empty worktree if no metadata tree found
- Adjust manual test instructions export to nitrate
- Export manual test case fields to nitrate
- Adjust the worktree implementation and test
- Implement shared worktree for the tests
- Adjust the improved verdict implementation
- Correct the verdict function, align docstring
- Print final image name in minute plugin
- Adjust the improved plan linting a bit
- Improve plan linting
- Implement port in Guest, show in verbose mode
- Use qemu user mode in the testcloud provision
- Support excluding packages during installation
- Support enabling/disabling plans and stories
- Do not link and remove general plans by default
- Improve general plans handling during test export
- Match by name prefix in discover.modified-only
- Passthrough non-zero exits for beakerlib execution
- Adjust the dry mode implementation for tmt init
- Implement dry mode for the tmt init command
- Do not use the spec release for the pip version
- Simplify story, plan and test search methods
- Do not use mutable objects as default arguments
- Prevent duplicate content in generated docs
- Ignore the nitrate migration warning during import
- Better summary for new exported tests
- Adjust exception handling in the testcloud plugin
- Make the testcloud ProvisionError more verbose
- Use IPv6 enabled 1MT network by default
- Improve debugging of tests using click runner
- Fix step selection for --before and --after
- Adjust the prepare test and pull/push enhancements
- Add prepare/shell test and pull/push enhancements
- Test filter on command line overrides config
- Improve handling of verbose and debug options
- Verify automated test case import from nitrate
- Enable copr repo even if no package is provided
- Improve documentation of tests, plans and stories
- Use fmf to store the newly created nitrate case id
- Adjust the hint about increasing the test duration
- Add hint to stdout in case of timeout
- Catch all exceptions when evaluating --condition
- Fix missing overview on the readthedocs.org site
- Adjust style of the new nitrate integration test
- Nitrate integration testsuite with requre
- Always enable force mode for display/html report
- Improve documentation, clearly show draft stories
- Test filter on command line overrides config
- Print unofficial attributes in tmt tests show -vv
- Adjust dry mode fix for test/plan/story create
- Implement dry mode for tmt test/plan/story create
- Support NO_COLOR to disable colored output
- Add test duration to `results.yaml`
- Adjust checking for duplicates during test export
- Prevent creating duplicate test cases in Nitrate
- Use singular for 'gate' as defined in the spec
- Fix gates conversion & drop artifacts
- Adjust a bit the shell completion instructions
- Describe how to enable shell completions
- Extend the duration test to cover positive results
- Detect timeout for Beakerlib, use TESTRESULT_STATE
- Improve tmt test path linting
- Clarify playbook path for ansible prepare plugin
- Adjust warning about the invalid disabled step
- Only warn on invalid disabled step
- Use date-service to get correct instantiation time
- Prevent keys mutation when searching plans/stories
- Cache fmf_id property
- Store relevant bugs during test import
- Avoid mutating `keys` default in .tests()
- Use the new execute method syntax for tmt tests
- Clean up obsolete test metadata

* Thu Feb 25 2021 Petr Šplíchal <psplicha@redhat.com> - 1.3.1-1
- Add test for prepare freeze
- Make file descriptors non-blocking
- Update the specification and stories to use link
- Implement the new core attribute 'link'

* Tue Feb 23 2021 Petr Šplíchal <psplicha@redhat.com> - 1.3.0-1
- Set timeout on select calls in utils._run()
- Show the current tmt version in the debug log
- Revert support for the 'el' distro shortcut
- Strip whitespace before relevancy comment
- Ensure rsync is installed on the guest if needed
- Use the default branch in the discover fmf plugin
- Suport the 'el' shortcut for the distro context
- Implement the 'tmt --version' option [fix #445]
- Adjust test create test, fix missing dots
- Support creating tests in the current directory
- Rename container images, update install docs
- Fixup Dockerfiles to build in quay.io.
- Support building mini and full tmt container image
- Add a Dockerfile for container with tmt
- Fix dependency error messages
- Use a better trigger name for source code changes
- Add a new 'Check Report' section to examples
- Add the --force explanation in the documentation
- Extend the test coverage to check for active runs
- Add basic test coverage for tmt status
- Restore context after processing each run
- Correctly handle an undefined step status
- Load default plan when no root is present
- Implement tmt status command
- Define command-line interface for status command
- Print library in error message during ref conflict
- Adjust the default branch handling for libraries
- Handle default branch in Library
- Adjust test duration, clean up old test metadata
- Improve timeout handling (fix an infinite loop)
- Adjust default timeout in the testcloud provision
- Remove obsolete unit test coverage for steps
- Adjust the filtering support, fix docs building
- Allow filtering using custom L1 metadata
- Allow filtering with lowercase bool names
- Handle exceptions when applying filters and conditions
- Share code for filters & conditions, test coverage
- Apply filters after applying defaults and conversions
- Fix IPv4 parsing when booting minute machine
- Remove all hacks for the old cruncher executor
- Remove the whole rhts-lint line during test import
- Remove the old convert test from unit tests
- Adjust contact handling to work with manual tests
- Fix contacts without name during tmt test import
- Finalize the specification of the 'link' attribute
- Add specification of the new core attribute 'link'
- Enough of dreaming, let's go to the forest! :)
- Update the overview of core classes, minor cleanup
- Add missing required packages for pip install
- Implement tmt run --follow option for checking log
- Extra check for required packages when using yum
- Clean up obsolete names in examples and templates
- Update the test checking for relevancy conversion
- Adjust storing test case id for new nitrate cases
- Append nitrate id when exporting instead of rewrite
- Skip prereserve check if custom flavor requested
- Use special compare operators only if minor given
- Adjust support for selecting modified tests
- Allow selecting only tests that have changed in git
- Remove the duplicate build job from packit config
- Verify the old beakerlib functions using Makefile
- Enable debug output using the TMT_DEBUG variable

* Fri Dec 11 2020 Petr Šplíchal <psplicha@redhat.com> - 1.2.1-1
- Manual state for manual nitrate tests
- Define framework for all beakerlib libraries tests
- Remove the remaining test case relevancy leftovers

* Wed Dec 09 2020 Petr Šplíchal <psplicha@redhat.com> - 1.2-1
- Minor adjustment of the beakerlib test template
- Adjust the new test checking the error output
- Print errors to stderr
- Fix check for selecting plans during tmt run
- Update test coverage, fix finish step example
- Update spec/stories implementation coverage
- Skip import of manual cases with script
- Import header and footer from Nitrate
- Implement conversion between relevancy and adjust
- Support short options for selecting tests & plans
- Document the display and html report in the spec
- Explain the difference between fmf and tmt
- Fix the last missing framework in library tests
- Adjust the docs update and title implementation
- Implement a new story attribute 'title' (L3)
- Small documentation cleanup
- Simplify plan setup, move old plans to examples
- Store the whole debug log in the top run directory
- Add test for pip installability
- Add a new plan to cover minimal installation
- Move html report plugin into a separate subpackage
- Use 'output.txt' filename for the main test output
- Update required fmf version in setup.py
- Improve the css style for the html report
- Fix blocking read in Common.run
- Adjust a bit the improved html report
- Improve report-html --open
- Implement adjusting metadata based on the context
- Adjust the new 'html' report method
- New report --how html available
- Adjust environment import from Makefile metadata
- Import environment from Makefile metadata
- Update old beakerlib paths during tmt test import
- Adjust a little bit the user story templates
- Support libraries stored deep in the repositories
- Enable the new coverage stories section in docs
- First stories to cover tests coverage mapping
- Recommend using login shell in libvirt hints
- Use nitrate naming for the manual field export
- Export manual attribute to nitrate
- Store complete initialized data in metadata.yaml
- Merge the improved minute error messages [#425]
- Adjust a bit the minute provision error messages
- Handle testcloud problem with the images directory
- Handle tracebacks in minute provision
- Multiple enhancements for package preparation
- Gracefully handle invalid library reference

* Thu Oct 22 2020 Petr Šplíchal <psplicha@redhat.com> - 1.1-1
- Convert adds extra-summary as well
- Simplify test directory copy with enabled symlinks
- Select latest minute image only from released images
- Allow specifying exact RHEL version using a short name
- Preserve symlinks during discover, pull and push
- Always run Login plugin even if step is done
- Suggest some useful aliases for common use cases
- Correct type of Tier attribute in examples
- Define basic hardware environment specification
- Import manual data for automated tests
- Tag tests which can be run under container/virtual
- Give hints to install provision plugins [fix #405]
- Handle nicely missing library metadata [fix #397]
- Update the test data directory name in the spec
- Extend duration for tests using virtualization
- Use a better name for the test data path method
- Provide aggregated test metadata for execution
- Send warnings to stderr, introduce a fail() method

* Wed Oct 07 2020 Petr Šplíchal <psplicha@redhat.com> - 1.0-1
- Correctly handle framework for new plans and tests
- Move runtest.sh adjustments into a single function
- Add the executable permission to runtest.sh
- Less strict removing sourcing of rhts-environment
- Use metadata directory as the default for path
- Implement the new L1 attribute 'framework'
- Explicitly enable copr_build for pull requests
- Handle missing library in existing repository
- Update the overall tmt description and examples
- Enable builds from master in the main copr repo
- Merge packit config for copr builds from master
- Use packit repository for copr builds from master
- Gracefully handle invalid test output
- Build in COPR for master via packit
- Add hint about caching the dnf package metadata
- Add two hints about easy login for experimenting
- Merge debug messages for the minute plugin [#361]
- Adjust the minute provision debug messages wording
- Use the internal tmt executor by default
- Add more debug messages to minute provision
- Remove the remaining 'tmt test convert' references
- Prevent shebang mangling for detached executor
- Merge the minute and install plugin docs [#345]
- Adjust the minute and install plugin documentation
- Merge the manual test import documentation [#347]
- Adjust the manual test documentation wording
- Merge rhts-environment source line removal [#344]
- Adjust rhts-environment source line removal
- Add missing extra-* keys to the test import
- Add docs for manual case import
- Disable authentication when fetching libraries
- Document the install prepare method
- Document the minute provision method
- Remove sourcing of rhts-environment in runtest.sh
- Add minute to supported provision methods of prepare

* Mon Sep 07 2020 Petr Šplíchal <psplicha@redhat.com> - 0.21-1
- Adjust manual test case import from nitrate [#319]
- Move the test convert deps into a separate package
- Support importing manual test cases from Nitrate
- Merge the non-zero exit codes for linting errors
- Fix several test export issues [fix #337]
- Adjust distro checks, remove the dry parameter
- Generalized Guest.details() [fix #310]
- Adjust the test coverage for tmt plan/test lint
- Update documentation with virtualization tips
- Make sure the duration timer is always canceled
- Merge the new retry_session functionality [#328]
- Exit with non-zero code if linting fails
- Merge fix for the double fmf extension [#327]
- Prevent koji from trying to build packages on i686
- Retry requests in case of network failure
- Avoid double fmf extension when creating plans and stories
- Improve the maximum test duration handling
- Remove vagrant from tmt-all recommended packages
- Detect beakerlib libraries from recommend as well
- Simplify packit custom create archive command
- Make the httpd test example a bit more interesting
- Append dots to fix tmt run --help message summary
- Document multiple configs and extending steps

* Tue Jul 28 2020 Petr Šplíchal <psplicha@redhat.com> - 0.20-1
- Move libraries handling into a separate module
- Adjust loading variables from YAML files [#316]
- Support environment variables from YAML files
- Give a nice error for expired kerberos [fix #57]
- Merge Guest relocation and documentation [#307]
- Describe essential Guest methods in more detail
- Update test import story and documentation
- Merge extra-task as summary in test export [#304]
- Move default plan handling into a single method
- Move the Guest class from base to steps.provision
- Save root in run.yaml
- Document L1 metadata defined in the discover step
- Improve Makefile editing during test import
- Use extra-task as summary in test export
- Mention default methods in the step help message
- Handle invalid url when library provided as fmf id
- Allow library git clone to fail

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
