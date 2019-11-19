%global srcname avocado

# Conditional for release vs. snapshot builds. Set to 1 for release build.
%if ! 0%{?rel_build:1}
    %global rel_build 1
%endif

# Settings used for build from snapshots.
%if 0%{?rel_build}
    %global gittar          %{srcname}-%{version}.tar.gz
%else
    %if ! 0%{?commit:1}
        %global commit     547139bfd042bcf259c66ff11d2be8d65a6386cd
    %endif
    %if ! 0%{?commit_date:1}
        %global commit_date 20190917
    %endif
    %global shortcommit     %(c=%{commit};echo ${c:0:8})
    %global gitrel          .%{commit_date}git%{shortcommit}
    %global gittar          %{srcname}-%{shortcommit}.tar.gz
%endif

# Selftests are provided but may need to be skipped because many of
# the functional tests are time and resource sensitive and can
# cause race conditions and random build failures. They are
# enabled by default.
%global with_tests 1

# Avocado is currently incompatible with the Fabric API in Fedora 31 and later
# https://github.com/avocado-framework/avocado/issues/3125
%if 0%{?fedora} >= 31
%global with_fabric 0
%else
%global with_fabric 1
%endif

# Python 3 version of Fabric package is new starting with Fedora 29
%if 0%{?fedora} >= 29
%global with_python3_fabric 1
%else
%global with_python3_fabric 0
%endif

# Python 3 version of aexpect is available on a module on Fedora >= 30
# and package build dependency resolution seems to be currently broken
# for modules.  Other developers have reported similar scenarios as this:
# https://lists.fedoraproject.org/archives/list/devel@lists.fedoraproject.org/thread/V6SBSAS5TBGNORGLYW75TIRX6JDBXQ2Q/
%if 0%{?fedora} >= 30 || 0%{?rhel}
%global with_python3_aexpect 0
%else
%global with_python3_aexpect 1
%endif

# The Python dependencies are already tracked by the python2
# or python3 "Requires".  This filters out the python binaries
# from the RPM automatic requires/provides scanner.
%global __requires_exclude ^/usr/bin/python[23]$

Summary: Framework with tools and libraries for Automated Testing
Name: python-%{srcname}
Version: 72.0
Release: 2%{?gitrel}%{?dist}
License: GPLv2
Group: Development/Tools
URL: http://avocado-framework.github.io/
%if 0%{?rel_build}
Source0: https://github.com/avocado-framework/%{srcname}/archive/%{version}.tar.gz#/%{gittar}
%else
Source0: https://github.com/avocado-framework/%{srcname}/archive/%{commit}.tar.gz#/%{gittar}
%endif
BuildArch: noarch
BuildRequires: procps-ng
BuildRequires: kmod
%if %{with_fabric}
%if %{with_python3_fabric}
BuildRequires: python3-fabric3
%endif
%endif # with_fabric
%if 0%{?fedora} >= 30
BuildRequires: glibc-all-langpacks
%endif
%if %{with_python3_aexpect}
BuildRequires: python3-aexpect
%endif

BuildRequires: python3-jinja2
BuildRequires: python3-devel
BuildRequires: python3-docutils
BuildRequires: python3-lxml
BuildRequires: python3-psutil
BuildRequires: python3-setuptools

%if ! 0%{?rhel}
BuildRequires: python3-resultsdb_api
BuildRequires: python3-pycdlib
%endif

%if %{with_tests}
BuildRequires: genisoimage
BuildRequires: libcdio
BuildRequires: psmisc
BuildRequires: python3-libvirt
BuildRequires: python3-yaml
BuildRequires: python3-netifaces
%if ! 0%{?rhel}
BuildRequires: perl-Test-Harness
%endif
%endif

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%package -n python3-%{srcname}
Summary: %{summary}
Requires: python3-%{srcname}-common == %{version}
Requires: gdb
Requires: gdb-gdbserver
Requires: procps-ng
Requires: python3
Requires: python3-setuptools
%if ! 0%{?rhel}
Requires: python3-pycdlib
%endif

%description -n python3-%{srcname}
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%prep
%if 0%{?rel_build}
%setup -q -n %{srcname}-%{version}
%else
%setup -q -n %{srcname}-%{commit}
%endif

%build
%if (0%{?fedora} && 0%{?fedora} < 29) || 0%{?rhel}
sed -e "s/'PyYAML>=4.2b2'/'PyYAML>=3.12'/" -i optional_plugins/varianter_yaml_to_mux/setup.py
%endif
%if 0%{?rhel}
%{__rm} -f avocado/etc/avocado/conf.d/resultsdb.conf
%endif
%py3_build
pushd optional_plugins/html
%py3_build
popd
pushd optional_plugins/runner_remote
%if %{with_fabric}
%if %{with_python3_fabric}
%py3_build
%endif
%endif # with_fabric
popd
pushd optional_plugins/runner_vm
%if %{with_fabric}
%if %{with_python3_fabric}
%py3_build
%endif
%endif # with_fabric
popd
pushd optional_plugins/runner_docker
%if %{with_python3_aexpect}
%if %{with_fabric}
%if %{with_python3_fabric}
%py3_build
%endif
%endif # with_fabric
%endif # with_python3_aexpect
popd
%if ! 0%{?rhel}
pushd optional_plugins/resultsdb
%py3_build
popd
%endif
pushd optional_plugins/varianter_yaml_to_mux
%py3_build
popd
pushd optional_plugins/loader_yaml
%py3_build
popd
pushd optional_plugins/golang
%py3_build
popd
pushd optional_plugins/varianter_pict
%py3_build
popd
pushd optional_plugins/varianter_cit
%py3_build
popd
pushd optional_plugins/result_upload
%py3_build
popd
pushd optional_plugins/glib
%py3_build
popd
# python3-docutils on Fedora 28 uses a rst2man binary with -3 prefix
%if 0%{?fedora} == 28
/usr/bin/rst2man-3 man/avocado.rst man/avocado.1
%else
%{__make} man
%endif

%install
%py3_install
%{__mv} %{buildroot}%{python3_sitelib}/avocado/etc %{buildroot}
pushd optional_plugins/html
%py3_install
popd
pushd optional_plugins/runner_remote
%if %{with_fabric}
%if %{with_python3_fabric}
%py3_install
%endif
%endif # with_fabric
popd
pushd optional_plugins/runner_vm
%if %{with_fabric}
%if %{with_python3_fabric}
%py3_install
%endif
%endif # with_fabric
popd
pushd optional_plugins/runner_docker
%if %{with_python3_aexpect}
%if %{with_fabric}
%if %{with_python3_fabric}
%py3_install
%endif
%endif # with_fabric
%endif # with_python3_aexpect
popd
%if ! 0%{?rhel}
pushd optional_plugins/resultsdb
%py3_install
popd
%endif
pushd optional_plugins/varianter_yaml_to_mux
%py3_install
popd
pushd optional_plugins/loader_yaml
%py3_install
popd
pushd optional_plugins/golang
%py3_install
popd
pushd optional_plugins/varianter_pict
%py3_install
popd
pushd optional_plugins/varianter_cit
%py3_install
popd
pushd optional_plugins/result_upload
%py3_install
popd
pushd optional_plugins/glib
%py3_install
popd
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
%{__install} -d -m 0755 %{buildroot}%{_sharedstatedir}/avocado/data
%{__install} -d -m 0755 %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/gdb-prerun-scripts %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/plugins %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/tests %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/wrappers %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/yaml_to_mux %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/yaml_to_mux_loader %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/varianter_pict %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/varianter_cit %{buildroot}%{_docdir}/avocado
find %{buildroot}%{_docdir}/avocado -type f -name '*.py' -exec %{__chmod} -c -x {} ';'
%{__mkdir} -p %{buildroot}%{_libexecdir}/avocado
%{__mv} %{buildroot}%{python3_sitelib}/avocado/libexec/* %{buildroot}%{_libexecdir}/avocado

%check
%if %{with_tests}
%{__python3} setup.py develop --user
pushd optional_plugins/html
%{__python3} setup.py develop --user
popd
%if %{with_fabric}
%if %{with_python3_fabric}
pushd optional_plugins/runner_remote
%{__python3} setup.py develop --user
popd
pushd optional_plugins/runner_vm
%{__python3} setup.py develop --user
popd
pushd optional_plugins/runner_docker
%if %{with_python3_aexpect}
%{__python3} setup.py develop --user
%endif # with_python3_aexpect
popd
%endif # with_python3_fabric
%endif # with_fabric
%if ! 0%{?rhel}
pushd optional_plugins/resultsdb
%{__python3} setup.py develop --user
popd
%endif
pushd optional_plugins/varianter_yaml_to_mux
%{__python3} setup.py develop --user
popd
pushd optional_plugins/loader_yaml
%{__python3} setup.py develop --user
popd
pushd optional_plugins/golang
%{__python3} setup.py develop --user
popd
pushd optional_plugins/varianter_pict
%{__python3} setup.py develop --user
popd
pushd optional_plugins/varianter_cit
%{__python3} setup.py develop --user
popd
pushd optional_plugins/result_upload
%{__python3} setup.py develop --user
popd
pushd optional_plugins/glib
%{__python3} setup.py develop --user
popd
# LANG: to make the results predictable, we pin the language
# that is used during test execution.
# AVOCADO_CHECK_LEVEL: package build environments have the least
# amount of resources we have observed so far.  Let's avoid tests that
# require too much resources or are time sensitive
# UNITTEST_AVOCADO_CMD: the "avocado" command to be run during
# unittests needs to be a Python specific one on Fedora >= 28.  Let's
# use the one that was setup in the source tree by the "setup.py
# develop --user" step and is guaranteed to be version specific.
LANG=en_US.UTF-8 AVOCADO_CHECK_LEVEL=0 UNITTEST_AVOCADO_CMD=$HOME/.local/bin/avocado %{__python3} selftests/run
%endif

%files -n python3-%{srcname}
%defattr(-,root,root,-)
%doc README.rst LICENSE
%{_bindir}/avocado
%{_bindir}/avocado-runner
%{_bindir}/avocado-runner-noop
%{_bindir}/avocado-runner-exec
%{_bindir}/avocado-runner-exec-test
%{_bindir}/avocado-runner-python-unittest
%{_bindir}/avocado-runner-avocado-instrumented
%{python3_sitelib}/avocado*
%exclude %{python3_sitelib}/avocado_result_html*
%exclude %{python3_sitelib}/avocado_runner_remote*
%exclude %{python3_sitelib}/avocado_runner_vm*
%exclude %{python3_sitelib}/avocado_runner_docker*
%exclude %{python3_sitelib}/avocado_resultsdb*
%exclude %{python3_sitelib}/avocado_loader_yaml*
%exclude %{python3_sitelib}/avocado_golang*
%exclude %{python3_sitelib}/avocado_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_varianter_pict*
%exclude %{python3_sitelib}/avocado_varianter_cit*
%exclude %{python3_sitelib}/avocado_result_upload*
%exclude %{python3_sitelib}/avocado_glib*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_html*
%exclude %{python3_sitelib}/avocado_framework_plugin_runner_remote*
%exclude %{python3_sitelib}/avocado_framework_plugin_runner_vm*
%exclude %{python3_sitelib}/avocado_framework_plugin_runner_docker*
%exclude %{python3_sitelib}/avocado_framework_plugin_resultsdb*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_pict*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_cit*
%exclude %{python3_sitelib}/avocado_framework_plugin_loader_yaml*
%exclude %{python3_sitelib}/avocado_framework_plugin_golang*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_upload*
%exclude %{python3_sitelib}/avocado_framework_plugin_glib*
%exclude %{python3_sitelib}/tests*

%package -n python3-%{srcname}-common
Summary: Avocado common files

%description -n python3-%{srcname}-common
Common files (such as configuration) for the Avocado Testing Framework.

%files -n python3-%{srcname}-common
%{_mandir}/man1/avocado.1.gz
%dir %{_sysconfdir}/avocado
%dir %{_sysconfdir}/avocado/conf.d
%dir %{_sysconfdir}/avocado/sysinfo
%dir %{_sysconfdir}/avocado/scripts
%dir %{_sysconfdir}/avocado/scripts/job
%dir %{_sysconfdir}/avocado/scripts/job/pre.d
%dir %{_sysconfdir}/avocado/scripts/job/post.d
%dir %{_sharedstatedir}/avocado
%config(noreplace)%{_sysconfdir}/avocado/avocado.conf
%config(noreplace)%{_sysconfdir}/avocado/conf.d/README
%config(noreplace)%{_sysconfdir}/avocado/conf.d/gdb.conf
%config(noreplace)%{_sysconfdir}/avocado/conf.d/jobscripts.conf
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/commands
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/files
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/profilers
%config(noreplace)%{_sysconfdir}/avocado/scripts/job/pre.d/README
%config(noreplace)%{_sysconfdir}/avocado/scripts/job/post.d/README

%package -n python3-%{srcname}-plugins-output-html
Summary: Avocado HTML report plugin
Requires: python3-%{srcname} == %{version}, python3-jinja2

%description -n python3-%{srcname}-plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files -n python3-%{srcname}-plugins-output-html
%{python3_sitelib}/avocado_result_html*
%{python3_sitelib}/avocado_framework_plugin_result_html*

%if %{with_fabric}
%if %{with_python3_fabric}
%package -n python3-%{srcname}-plugins-runner-remote
Summary: Avocado Runner for Remote Execution
Requires: python3-%{srcname} == %{version}
Requires: python3-fabric3

%description -n python3-%{srcname}-plugins-runner-remote
Allows Avocado to run jobs on a remote machine, by means of an SSH
connection.  Avocado must be previously installed on the remote machine.

%files -n python3-%{srcname}-plugins-runner-remote
%{python3_sitelib}/avocado_runner_remote*
%{python3_sitelib}/avocado_framework_plugin_runner_remote*
%endif # with_python3_fabric
%endif # with_fabric

%if %{with_fabric}
%if %{with_python3_fabric}
%package -n python3-%{srcname}-plugins-runner-vm
Summary: Avocado Runner for libvirt VM Execution
Requires: python3-%{srcname} == %{version}
Requires: python3-%{srcname}-plugins-runner-remote == %{version}
Requires: python3-libvirt

%description -n python3-%{srcname}-plugins-runner-vm
Allows Avocado to run jobs on a libvirt based VM, by means of
interaction with a libvirt daemon and an SSH connection to the VM
itself.  Avocado must be previously installed on the VM.

%files -n python3-%{srcname}-plugins-runner-vm
%{python3_sitelib}/avocado_runner_vm*
%{python3_sitelib}/avocado_framework_plugin_runner_vm*
%endif # with_python3_fabric
%endif # with_fabric

%if %{with_python3_aexpect}
%if %{with_fabric}
%if %{with_python3_fabric}
%package -n python3-%{srcname}-plugins-runner-docker
Summary: Avocado Runner for Execution on Docker Containers
Requires: python3-%{srcname} == %{version}
Requires: python3-%{srcname}-plugins-runner-remote == %{version}
Requires: python3-aexpect

%description -n python3-%{srcname}-plugins-runner-docker
Allows Avocado to run jobs on a Docker container by interacting with a
Docker daemon and attaching to the container itself.  Avocado must
be previously installed on the container.

%files -n python3-%{srcname}-plugins-runner-docker
%{python3_sitelib}/avocado_runner_docker*
%{python3_sitelib}/avocado_framework_plugin_runner_docker*
%endif # with_python3_fabric
%endif # with_fabric
%endif # with_python3_aexpect

%if ! 0%{?rhel}
%package -n python3-%{srcname}-plugins-resultsdb
Summary: Avocado plugin to propagate job results to ResultsDB
Requires: python3-%{srcname} == %{version}
Requires: python3-resultsdb_api

%description -n python3-%{srcname}-plugins-resultsdb
Allows Avocado to send job results directly to a ResultsDB
server.

%files -n python3-%{srcname}-plugins-resultsdb
%{python3_sitelib}/avocado_resultsdb*
%{python3_sitelib}/avocado_framework_plugin_resultsdb*
%config(noreplace)%{_sysconfdir}/avocado/conf.d/resultsdb.conf
%endif

%package -n python3-%{srcname}-plugins-varianter-yaml-to-mux
Summary: Avocado plugin to generate variants out of yaml files
Requires: python3-%{srcname} == %{version}
Requires: python3-yaml

%description -n python3-%{srcname}-plugins-varianter-yaml-to-mux
Can be used to produce multiple test variants with test parameters
defined in a yaml file(s).

%files -n python3-%{srcname}-plugins-varianter-yaml-to-mux
%{python3_sitelib}/avocado_varianter_yaml_to_mux*
%{python3_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*

%package -n python3-%{srcname}-plugins-loader-yaml
Summary: Avocado Plugin that loads tests from YAML files
Requires: python3-%{srcname}-plugins-varianter-yaml-to-mux == %{version}

%description -n python3-%{srcname}-plugins-loader-yaml
Can be used to produce a test suite from definitions in a YAML file,
similar to the one used in the yaml_to_mux varianter plugin.

%files -n python3-%{srcname}-plugins-loader-yaml
%{python3_sitelib}/avocado_loader_yaml*
%{python3_sitelib}/avocado_framework_plugin_loader_yaml*

%package -n python3-%{srcname}-plugins-golang
Summary: Avocado Plugin for Execution of golang tests
Requires: python3-%{srcname} == %{version}
Requires: golang

%description -n python3-%{srcname}-plugins-golang
Allows Avocado to list golang tests, and if golang is installed,
also run them.

%files -n python3-%{srcname}-plugins-golang
%{python3_sitelib}/avocado_golang*
%{python3_sitelib}/avocado_framework_plugin_golang*

%package -n python3-%{srcname}-plugins-varianter-pict
Summary: Varianter with combinatorial capabilities by PICT
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-plugins-varianter-pict
This plugin uses a third-party tool to provide variants created by
Pair-Wise algorithms, also known as Combinatorial Independent Testing.

%files -n python3-%{srcname}-plugins-varianter-pict
%{python3_sitelib}/avocado_varianter_pict*
%{python3_sitelib}/avocado_framework_plugin_varianter_pict*

%package -n python3-%{srcname}-plugins-varianter-cit
Summary: Varianter with Combinatorial Independent Testing capabilities
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-plugins-varianter-cit
A varianter plugin that generates variants using Combinatorial
Independent Testing (AKA Pair-Wise) algorithm developed in
collaboration with CVUT Prague.

%files -n python3-%{srcname}-plugins-varianter-cit
%{python3_sitelib}/avocado_varianter_cit*
%{python3_sitelib}/avocado_framework_plugin_varianter_cit*

%package -n python3-%{srcname}-plugins-result-upload
Summary: Avocado Plugin to propagate Job results to a remote host
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-plugins-result-upload
This optional plugin is intended to upload the Avocado Job results to
a dedicated sever.

%files -n python3-%{srcname}-plugins-result-upload
%{python3_sitelib}/avocado_result_upload*
%{python3_sitelib}/avocado_framework_plugin_result_upload*
%config(noreplace)%{_sysconfdir}/avocado/conf.d/result_upload.conf

%package -n python3-%{srcname}-plugins-glib
Summary: Avocado Plugin for Execution of GLib Test Framework tests
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-plugins-glib
This optional plugin is intended to list and run tests written in the
GLib Test Framework.

%files -n python3-%{srcname}-plugins-glib
%{python3_sitelib}/avocado_glib*
%{python3_sitelib}/avocado_framework_plugin_glib*
%config(noreplace)%{_sysconfdir}/avocado/conf.d/glib.conf

%package -n python3-%{srcname}-examples
Summary: Avocado Test Framework Example Tests
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-examples
The set of example tests present in the upstream tree of the Avocado framework.
Some of them are used as functional tests of the framework, others serve as
examples of how to write tests on your own.

%files -n python3-%{srcname}-examples
%dir %{_docdir}/avocado
%{_docdir}/avocado/gdb-prerun-scripts
%{_docdir}/avocado/plugins
%{_docdir}/avocado/tests
%{_docdir}/avocado/wrappers
%{_docdir}/avocado/yaml_to_mux
%{_docdir}/avocado/yaml_to_mux_loader
%{_docdir}/avocado/varianter_pict
%{_docdir}/avocado/varianter_cit

%package -n python3-%{srcname}-bash
Summary: Avocado Test Framework Bash Utilities
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-bash
A small set of utilities to interact with Avocado from the Bourne
Again Shell code (and possibly other similar shells).

%files -n python3-%{srcname}-bash
%{_libexecdir}/avocado*

%changelog
* Mon Nov 18 2019 Cleber Rosa <cleber@redhat.com> - 72.0-2
- Add EL/EPEL8 support

* Fri Sep 27 2019 Cleber Rosa <cleber@redhat.com> - 72.0-1
- Added new avocado-runner-* runner scripts

* Tue Sep 17 2019 Cleber Rosa <cleber@redhat.com> - 72.0-0
- New release

* Thu Sep  5 2019 Cleber Rosa <cleber@redhat.com> - 71.0-2
- Added nrunner standalone scripts

* Mon Aug 19 2019 Cleber Rosa <cleber@redhat.com> - 71.0-1
- Use newer libvirt Python bindings package name
- Dropped older libvirt Python lack of egg info workaround

* Thu Aug 15 2019 Cleber Rosa <cleber@redhat.com> - 71.0-0
- New release

* Tue Jul  9 2019 Cleber Rosa <cleber@redhat.com> - 70.0-1
- Add config file to glib plugin subpackage

* Wed Jun 26 2019 Cleber Rosa <cleber@redhat.com> - 70.0-0
- New release

* Tue Jun 25 2019 Cleber Rosa <cleber@redhat.com> - 69.0-3
- Drop python3-sphinx build requirement
- Cleaned up some of the changelog history

* Tue Jun 25 2019 Cleber Rosa <cleber@redhat.com> - 69.0-2
- Build without python3-aexpect on Fedora 30 and later

* Tue May 28 2019 Merlin Mathesius <mmathesi@redhat.com> - 69.0-1
- Disable components dependent upon Fiber in Fedora 31 and later,
  since avocado is currently incompatible with the new Fiber API.
- Remove pyliblzma as it has always been Python 2-only, and it is
  no longer available as of F31.

* Tue Feb 26 2019 Cleber Rosa <cleber@redhat.com> - 69.0-0
- New release
