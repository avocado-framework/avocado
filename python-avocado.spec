%global srcname avocado

# Conditional for release vs. snapshot builds. Set to 1 for release build.
%if ! 0%{?rel_build:1}
    %global rel_build 1
%endif

# Settings used for build from snapshots.
%if 0%{?rel_build}
    %global gittar		%{srcname}-%{version}.tar.gz
%else
    %if ! 0%{?commit:1}
        %global commit		b066ee5ae204e4bd2eefd59151c8fb2a453aa47d
    %endif
    %if ! 0%{?commit_date:1}
        %global commit_date	20170518
    %endif
    %global shortcommit	%(c=%{commit};echo ${c:0:7})
    %global gitrel		.%{commit_date}git%{shortcommit}
    %global gittar		%{srcname}-%{shortcommit}.tar.gz
%endif

# Selftests are provided but may need to be skipped because many of
# the functional tests are time and resource sensitive and can
# cause race conditions and random build failures. They are
# enabled by default.
%global with_tests 1

Summary: Framework with tools and libraries for Automated Testing
Name: python-%{srcname}
Version: 52.0
Release: 0%{?gitrel}%{?dist}
License: GPLv2
Group: Development/Tools
URL: http://avocado-framework.github.io/
%if 0%{?rel_build}
Source0: https://github.com/avocado-framework/%{srcname}/archive/%{version}.tar.gz#/%{gittar}
%else
Source0: https://github.com/avocado-framework/%{srcname}/archive/%{commit}.tar.gz#/%{gittar}
%endif
BuildArch: noarch
BuildRequires: fabric
BuildRequires: procps-ng
BuildRequires: pystache
BuildRequires: python-docutils
BuildRequires: python-flexmock
BuildRequires: python-lxml
BuildRequires: python-mock
BuildRequires: python-psutil
BuildRequires: python-requests
BuildRequires: python-resultsdb_api
BuildRequires: python-setuptools
BuildRequires: python-sphinx
BuildRequires: python-stevedore
BuildRequires: python2-devel
BuildRequires: yum

%if %{with_tests}
BuildRequires: libvirt-python
BuildRequires: perl-Test-Harness
%endif

Requires: gdb
Requires: gdb-gdbserver
Requires: procps-ng
Requires: pyliblzma
Requires: python
Requires: python-requests
Requires: python-setuptools
Requires: python-stevedore
%if 0%{?fedora}
BuildRequires: python-aexpect
%else
BuildRequires: aexpect
%endif

# For compatibility reasons, let's mark this package as one that
# provides the same functionality as the old package name and also
# one that obsoletes the old package name, so that the new name is
# favored.  These could (and should) be removed in the future.
# These changes are backed by the following guidelines:
# https://fedoraproject.org/wiki/Upgrade_paths_%E2%80%94_renaming_or_splitting_packages
Obsoletes: %{srcname} < 47.0-1
Provides: %{srcname} = %{version}-%{release}

# For some strange reason, fabric on Fedora 24 does not require the
# python-crypto package, but the fabric code always imports it.  Newer
# fabric versions, such from Fedora 25 do conditional imports (try:
# from Crypto import Random; except: Random = None) and thus do not
# need this requirement.
%if 0%{?fedora} == 24
BuildRequires: python-crypto
%endif

%if 0%{?fedora} >= 25
BuildRequires: kmod
%endif
%if 0%{?rhel} >= 7
BuildRequires: kmod
%endif

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%prep
%if 0%{?rel_build}
%setup -q -n %{srcname}-%{version}
%else
%setup -q -n %{srcname}-%{commit}
%endif
# package plugins-runner-vm requires libvirt-python, but the RPM
# version of libvirt-python does not publish the egg info and this
# causes that dep to be attempted to be installed by pip
sed -e "s/'libvirt-python'//" -i optional_plugins/runner_vm/setup.py

%build
%{__python} setup.py build
pushd optional_plugins/html
%{__python} setup.py build
popd
pushd optional_plugins/runner_remote
%{__python} setup.py build
popd
pushd optional_plugins/runner_vm
%{__python} setup.py build
popd
pushd optional_plugins/runner_docker
%{__python} setup.py build
popd
pushd optional_plugins/resultsdb
%{__python} setup.py build
popd
pushd optional_plugins/varianter_yaml_to_mux
%{__python} setup.py build
popd
%{__make} man

%install
%{__python} setup.py install --root %{buildroot} --skip-build
pushd optional_plugins/html
%{__python} setup.py install --root %{buildroot} --skip-build
popd
pushd optional_plugins/runner_remote
%{__python} setup.py install --root %{buildroot} --skip-build
popd
pushd optional_plugins/runner_vm
%{__python} setup.py install --root %{buildroot} --skip-build
popd
pushd optional_plugins/runner_docker
%{__python} setup.py install --root %{buildroot} --skip-build
popd
pushd optional_plugins/resultsdb
%{__python} setup.py install --root %{buildroot} --skip-build
popd
pushd optional_plugins/varianter_yaml_to_mux
%{__python} setup.py install --root %{buildroot} --skip-build
popd
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
%{__install} -m 0644 man/avocado-rest-client.1 %{buildroot}%{_mandir}/man1/avocado-rest-client.1
%{__install} -d -m 0755 %{buildroot}%{_sharedstatedir}/avocado/data

%check
%if %{with_tests}
%{__python} setup.py develop --user
pushd optional_plugins/html
%{__python} setup.py develop --user
popd
pushd optional_plugins/runner_remote
%{__python} setup.py develop --user
popd
pushd optional_plugins/runner_vm
%{__python} setup.py develop --user
popd
pushd optional_plugins/runner_docker
%{__python} setup.py develop --user
popd
pushd optional_plugins/resultsdb
%{__python} setup.py develop --user
popd
pushd optional_plugins/varianter_yaml_to_mux
%{__python} setup.py develop --user
popd
# Package build environments have the least amount of resources
# we have observed so far.  Let's avoid tests that require too
# much resources or are time sensitive
AVOCADO_CHECK_LEVEL=0 selftests/run
%endif

%files
%defattr(-,root,root,-)
%doc README.rst LICENSE
%dir /etc/avocado
%dir /etc/avocado/conf.d
%dir /etc/avocado/sysinfo
%dir /etc/avocado/scripts/job/pre.d
%dir /etc/avocado/scripts/job/post.d
%dir %{_sharedstatedir}/avocado
%config(noreplace)/etc/avocado/avocado.conf
%config(noreplace)/etc/avocado/conf.d/README
%config(noreplace)/etc/avocado/conf.d/gdb.conf
%config(noreplace)/etc/avocado/sysinfo/commands
%config(noreplace)/etc/avocado/sysinfo/files
%config(noreplace)/etc/avocado/sysinfo/profilers
%config(noreplace)/etc/avocado/scripts/job/pre.d/README
%config(noreplace)/etc/avocado/scripts/job/post.d/README
%{python_sitelib}/avocado*
%{_bindir}/avocado
%{_bindir}/avocado-rest-client
%{_mandir}/man1/avocado.1.gz
%{_mandir}/man1/avocado-rest-client.1.gz
%{_docdir}/avocado/avocado.rst
%{_docdir}/avocado/avocado-rest-client.rst
%exclude %{python_sitelib}/avocado_result_html*
%exclude %{python_sitelib}/avocado_runner_remote*
%exclude %{python_sitelib}/avocado_runner_vm*
%exclude %{python_sitelib}/avocado_runner_docker*
%exclude %{python_sitelib}/avocado_resultsdb*
%exclude %{python_sitelib}/avocado_varianter_yaml_to_mux*
%exclude %{python_sitelib}/avocado_framework_plugin_result_html*
%exclude %{python_sitelib}/avocado_framework_plugin_runner_remote*
%exclude %{python_sitelib}/avocado_framework_plugin_runner_vm*
%exclude %{python_sitelib}/avocado_framework_plugin_runner_docker*
%exclude %{python_sitelib}/avocado_framework_plugin_resultsdb*
%exclude %{python_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*
%{_libexecdir}/avocado/avocado-bash-utils
%{_libexecdir}/avocado/avocado_debug
%{_libexecdir}/avocado/avocado_error
%{_libexecdir}/avocado/avocado_info
%{_libexecdir}/avocado/avocado_warn

%package plugins-output-html
Summary: Avocado HTML report plugin
Requires: %{name} == %{version}, pystache
Obsoletes: %{srcname}-plugins-output-html < 47.0-1
Provides: %{srcname}-plugins-output-html = %{version}-%{release}

%description plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files plugins-output-html
%{python_sitelib}/avocado_result_html*
%{python_sitelib}/avocado_framework_plugin_result_html*

%package plugins-runner-remote
Summary: Avocado Runner for Remote Execution
Requires: %{name} == %{version}
Requires: fabric
%if 0%{?fedora} == 24
Requires: python-crypto
BuildRequires: python-crypto
%endif
Obsoletes: %{srcname}-plugins-runner-remote < 47.0-1
Provides: %{srcname}-plugins-runner-remote = %{version}-%{release}

%description plugins-runner-remote
Allows Avocado to run jobs on a remote machine, by means of an SSH
connection.  Avocado must be previously installed on the remote machine.

%files plugins-runner-remote
%{python_sitelib}/avocado_runner_remote*
%{python_sitelib}/avocado_framework_plugin_runner_remote*

%package plugins-runner-vm
Summary: Avocado Runner for libvirt VM Execution
Requires: %{name} == %{version}
Requires: %{name}-plugins-runner-remote == %{version}
Requires: libvirt-python
Obsoletes: %{srcname}-plugins-runner-vm < 47.0-1
Provides: %{srcname}-plugins-runner-vm = %{version}-%{release}

%description plugins-runner-vm
Allows Avocado to run jobs on a libvirt based VM, by means of
interaction with a libvirt daemon and an SSH connection to the VM
itself.  Avocado must be previously installed on the VM.

%files plugins-runner-vm
%{python_sitelib}/avocado_runner_vm*
%{python_sitelib}/avocado_framework_plugin_runner_vm*

%package plugins-runner-docker
Summary: Avocado Runner for Execution on Docker Containers
Requires: %{name} == %{version}
Requires: %{name}-plugins-runner-remote == %{version}
%if 0%{?fedora}
Requires: python-aexpect
%else
Requires: aexpect
%endif
Obsoletes: %{srcname}-plugins-runner-docker < 47.0-1
Provides: %{srcname}-plugins-runner-docker = %{version}-%{release}

%description plugins-runner-docker
Allows Avocado to run jobs on a Docker container by interacting with a
Docker daemon and attaching to the container itself.  Avocado must
be previously installed on the container.

%files plugins-runner-docker
%{python_sitelib}/avocado_runner_docker*
%{python_sitelib}/avocado_framework_plugin_runner_docker*

%package plugins-resultsdb
Summary: Avocado plugin to propagate job results to ResultsDB
Requires: %{name} == %{version}
Requires: python-resultsdb_api

%description plugins-resultsdb
Allows Avocado to send job results directly to a ResultsDB
server.

%files plugins-resultsdb
%{python_sitelib}/avocado_resultsdb*
%{python_sitelib}/avocado_framework_plugin_resultsdb*

%package plugins-varianter-yaml-to-mux
Summary: Avocado plugin to generate variants out of yaml files
Requires: %{name} == %{version}
Requires: python-yaml

%description plugins-varianter-yaml-to-mux
Can be used to produce multiple test variants with test parameters
defined in a yaml file(s).

%files plugins-varianter-yaml-to-mux
%{python_sitelib}/avocado_varianter_yaml_to_mux*
%{python_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*

%package examples
Summary: Avocado Test Framework Example Tests
Requires: %{name} == %{version}

%description examples
The set of example tests present in the upstream tree of the Avocado framework.
Some of them are used as functional tests of the framework, others serve as
examples of how to write tests on your own.

%files examples
%{_datadir}/avocado/tests
%{_datadir}/avocado/wrappers

%changelog
* Mon Jun 26 2017 Cleber Rosa <cleber@redhat.com> - 52.0-0
- New upstream release

* Mon Jun 12 2017 Cleber Rosa <cleber@redhat.com> - 51.0-0
- New upstream release

* Fri May 19 2017 Lukas Doktor <ldoktor@redhat.com> - 50.0-1
- Separate the varianter_yaml_to_mux plugin to a separate RPM

* Tue May 16 2017 Cleber Rosa <cleber@redhat.com> - 50.0-0
- New upstream release

* Thu Apr 27 2017 Cleber Rosa <cleber@redhat.com> - 49.0-2
- Also setup resultsdb plugin on check
- Be explicit about selftest level run on check
- Take ownership of base avocado data dir (/var/lib/avocado)

* Tue Apr 25 2017 Cleber Rosa <cleber@redhat.com> - 49.0-1
- Added missing runner-docker directory

* Tue Apr 25 2017 Cleber Rosa <cleber@redhat.com> - 49.0-0
- New upstream release

* Mon Apr 24 2017 Cleber Rosa <cleber@redhat.com> - 48.0-5
- Add subpackage for resultsdb plugin

* Wed Apr 19 2017 Cleber Rosa <cleber@redhat.com> - 48.0-4
- Added "/var/lib/avocado" directory for writable content

* Wed Apr 19 2017 Cleber Rosa <cleber@redhat.com> - 48.0-3
- Fix exclusion of optional plugins files done on 48.0-1

* Mon Apr 10 2017 Cleber Rosa <cleber@redhat.com> - 48.0-2
- Update how release and snapshot packages are built

* Mon Apr  3 2017 Cleber Rosa <cleber@redhat.com> - 48.0-1
- Updated exclude directives and files for optional plugins

* Mon Apr  3 2017 Cleber Rosa <cleber@redhat.com> - 48.0-0
- New upstream release

* Fri Mar 31 2017 Cleber Rosa <cleber@redhat.com> - 47.0-2
- Switch directory change statements to match downstream
- Change requirements style to one per line
- Add conditional execution of selftests

* Wed Mar  8 2017 Cleber Rosa <cleber@redhat.com> - 47.0-1
- Rename package to python-avocado and subpackges accordingly

* Mon Mar  6 2017 Cleber Rosa <cleber@redhat.com> - 47.0-0
- New upstream release

* Wed Feb 15 2017 Cleber Rosa <cleber@redhat.com> - 46.0-2
- Removed python-crypto dependency from base avocado package

* Wed Feb 15 2017 Cleber Rosa <cleber@redhat.com> - 46.0-1
- Fixed packager email
- Added explicit requirement

* Tue Feb 14 2017 Cleber Rosa <cleber@redhat.com> - 46.0-0
- New upstream release

* Sun Feb  5 2017 Cleber Rosa <cleber@redhat.com> - 45.0-2
- Split package into plugins-runner-{remote,vm,docker} packages

* Fri Feb  3 2017 Cleber Rosa <cleber@redhat.com> - 45.0-1
- Removed support for EL6 requirements

* Tue Jan 17 2017 Cleber Rosa <cleber@redhat.com> - 45.0-0
- New upstream release

* Wed Dec  7 2016 Cleber Rosa <cleber@redhat.com> - 44.0-0
- New upstream release

* Tue Nov  8 2016 Cleber Rosa <cleber@redhat.com> - 43.0-0
- New upstream release

* Mon Oct 10 2016 Cleber Rosa <cleber@redhat.com> - 42.0-0
- New upstream release

* Fri Sep 16 2016 Cleber Rosa <cleber@redhat.com> - 41.0-1
- Consolidated build requires common to all targets
- Enabled check on EL6

* Mon Sep 12 2016 Cleber Rosa <cleber@redhat.com> - 41.0-0
- New upstream release

* Tue Sep  6 2016 Cleber Rosa <cleber@redhat.com> - 40.0-1
- Adapt build of now separate html plugin

* Tue Aug 16 2016 Cleber Rosa <cleber@redhat.com> - 40.0-0
- New upstream release

* Tue Aug  2 2016 Cleber Rosa <cleber@redhat.com> - 39.0-1
- Added expect requirement (for Docker plugin)

* Tue Jul 26 2016 Cleber Rosa <cleber@redhat.com> - 39.0-0
- New upstream release

* Mon Jul  4 2016 Cleber Rosa <cleber@redhat.com> - 38.0-0
- New upstream release

* Tue Jun 14 2016 Cleber Rosa <cleber@redhat.com> - 37.0-0
- New upstream release

* Thu May 05 2016 Amador Pahim <apahim@redhat.com> - 35.0-1
- Removed simpletests directory

* Wed Apr 27 2016 Cleber Rosa <cleber@redhat.com> - 35.0-0
- New upstream release 35.0 (new versioning scheme)

* Thu Apr 14 2016 Cleber Rosa <cleber@redhat.com> - 0.34.0-1
- Added job pre/post scripts directories

* Mon Mar 21 2016 Cleber Rosa <cleber@redhat.com> - 0.34.0-0
- New upstream release 0.34.0

* Wed Feb 17 2016 Cleber Rosa <cleber@redhat.com> - 0.33.0-1
- Updated requirement: procps for EL6, procps-ng for other distros

* Tue Feb 16 2016 Cleber Rosa <cleber@redhat.com> - 0.33.0-0
- New upstream release 0.33.0

* Wed Jan 20 2016 Cleber Rosa <cleber@redhat.com> - 0.32.0-0
- New upstream release 0.32.0

* Wed Dec 23 2015 Cleber Rosa <cleber@redhat.com> - 0.31.0-0
- New upstream release 0.31.0

* Tue Nov 17 2015 Cleber Rosa <cleber@redhat.com> - 0.30.0-1
- Add python-stevedore to Requires

* Thu Nov  5 2015 Cleber Rosa <cleber@redhat.com> - 0.30.0-0
- New upstream release 0.30.0

* Wed Oct 7 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.29.0-2
- Add python-setuptools to BuildRequires

* Wed Oct 7 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.29.0-1
- New upstream release 0.29.0

* Wed Sep 16 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.28.0-2
- Add pystache, aexpect, psutil, sphinx and yum/dnf dependencies for functional/unittests

* Wed Sep 16 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.28.0-1
- New upstream release 0.28.0

* Tue Aug 4 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.27.0-3
- Added 'gdb' and 'gdb-gdbserver' as requirements

* Mon Aug 3 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.27.0-2
- Added 'python-mock' as a build requirement

* Mon Aug 3 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.27.0-1
- New upstream release 0.27.0

* Mon Jul 6 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.26.0-1
- New upstream release 0.26.0

* Tue Jun 16 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.25.0-2
- Fix spec bug with BuildRequires on EPEL6

* Tue Jun 16 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.25.0-1
- New upstream release 0.25.0

* Fri Jun  5 2015 Cleber Rosa <cleber@redhat.com> - 0.24.0-3
- Removed rest client API examples

* Mon May 25 2015 Cleber Rosa <cleber@redhat.com> - 0.24.0-2
- Added previously missing gdb.conf

* Mon May 18 2015 Ruda Moura <rmoura@redhat.com> - 0.24.0-1
- Update to upstream version 0.24.0

* Tue Apr 21 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.23.0-1
- New upstream release

* Mon Apr 13 2015 Cleber Rosa <cleber@redhat.com> - 0.21.0-6
- Added sysinfo configuration files

* Sat Mar 28 2015 Cleber Rosa <cleber@redhat.com> - 0.21.0-5
- Change the way man pages are built, now using Makefile targets
- Reorganized runtime and build requirements
- Add a check section that runs unittests on Fedora

* Thu Mar 19 2015 Lucas Meneghel Rodrigues - 0.21.0-4
- COPR build fixes

* Mon Mar 16 2015 Lucas Meneghel Rodrigues - 0.21.0-3
- COPR build fixes

* Mon Mar 16 2015 Lucas Meneghel Rodrigues - 0.21.0-2
- COPR build fixes

* Mon Mar 16 2015 Lucas Meneghel Rodrigues - 0.21.0-1
- COPR build fixes

* Mon Mar 16 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.21.0-0
- Update to upstream version 0.21.0

* Mon Feb 23 2015 Cleber Rosa <cleber@redhat.com> - 0.20.1-2
- Added avocado-rest-client modules, script, man page and API examples

* Fri Feb 6 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.20.1-1
- Update to upstream version 0.20.1

* Tue Feb 3 2015 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.20.0-1
- Update to upstream version 0.20.0

* Mon Dec 15 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.17.0-1
- Update to upstream version 0.17.0

* Wed Dec  3 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.14.0-3
- Change config file name from settings.ini to avocado.conf

* Wed Dec  3 2014 Ruda Moura <rmoura@redhat.com> - 0.14.0-2
- Include all wrappers scripts to examples subpackage.

* Mon Oct 13 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.14.0-1
- New upstream release

* Thu Sep 11 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.12.0-2
- Rename -tests package to -examples

* Tue Sep  9 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.12.0-1
- New upstream release

* Tue Sep  2 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.11.1-2
- Added fabric dependency

* Wed Aug 20 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.11.1-1
- Bumped version to avocado 0.11.1
- Added python-yaml build dependency

* Wed Aug 20 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.11.0-1
- Bumped version to avocado 0.11.0
- Added python-yaml new dependency

* Wed Aug 20 2014 Cleber Rosa <cleber@redhat.com> - 0.10.1-2
- Added initial avocado man page

* Tue Aug 12 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.10.1-1
- Bugfix release 0.10.1

* Thu Aug  7 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.10.0-1
- Bumped version to Avocado 0.10.0

* Wed Jul 30 2014 Cleber Rosa <cleber@redhat.com> - 0.8.0-2
- Split tests into avocado-tests package

* Fri Jul 18 2014 Lucas Meneghel Rodrigues <lmr@redhat.com> - 0.8.0-1
- Bumped version to Avocado 0.8.0

* Fri Jun 13 2014 Ruda Moura <rmoura@redhat.com> - 0.6.0-1
- Bumped version to Avocado 0.6.0

* Thu May  8 2014 Ruda Moura <rmoura@redhat.com> - 0.4.0-1
- Bumped version to Avocado 0.4.0

* Wed Apr 30 2014 Cleber Rosa <cleber@redhat.com> - 0.0.1-2
- Added new requirements reflecting new upstream deps

* Wed Apr  2 2014 Ruda Moura <rmoura@redhat.com> - 0.0.1-1
- Created initial spec file
