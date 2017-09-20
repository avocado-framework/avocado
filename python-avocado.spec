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
        %global commit		1d4e7bdf857cf9408113a3a39cd327b4fe22c64c
    %endif
    %if ! 0%{?commit_date:1}
        %global commit_date	20170518
    %endif
    %global shortcommit	%(c=%{commit};echo ${c:0:8})
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
Version: 54.0
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
BuildRequires: python-aexpect

%if %{with_tests}
BuildRequires: libvirt-python
BuildRequires: perl-Test-Harness
%if 0%{?rhel}
BuildRequires: python-yaml
%else
BuildRequires: python2-yaml
%endif
%endif

Requires: gdb
Requires: gdb-gdbserver
Requires: procps-ng
Requires: pyliblzma
Requires: python
Requires: python-requests
Requires: python-setuptools
Requires: python-stevedore

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
pushd optional_plugins/loader_yaml
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
pushd optional_plugins/loader_yaml
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
pushd optional_plugins/loader_yaml
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
%dir %{_sysconfdir}/avocado
%dir %{_sysconfdir}/avocado/conf.d
%dir %{_sysconfdir}/avocado/sysinfo
%dir %{_sysconfdir}/avocado/scripts/job/pre.d
%dir %{_sysconfdir}/avocado/scripts/job/post.d
%dir %{_sharedstatedir}/avocado
%config(noreplace)%{_sysconfdir}/avocado/avocado.conf
%config(noreplace)%{_sysconfdir}/avocado/conf.d/README
%config(noreplace)%{_sysconfdir}/avocado/conf.d/gdb.conf
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/commands
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/files
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/profilers
%config(noreplace)%{_sysconfdir}/avocado/scripts/job/pre.d/README
%config(noreplace)%{_sysconfdir}/avocado/scripts/job/post.d/README
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
%exclude %{python_sitelib}/avocado_framework_plugin_loader_yaml*
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
Requires: python-aexpect
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
%if 0%{?rhel}
Requires: python-yaml
%else
Requires: python2-yaml
%endif

%description plugins-varianter-yaml-to-mux
Can be used to produce multiple test variants with test parameters
defined in a yaml file(s).

%files plugins-varianter-yaml-to-mux
%{python_sitelib}/avocado_varianter_yaml_to_mux*
%{python_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*

%package plugins-loader-yaml
Summary: Avocado Plugin that loads tests from YAML files
Requires: %{name}-plugins-varianter-yaml-to-mux == %{version}

%description plugins-loader-yaml
Can be used to produce a test suite from definitions in a YAML file,
similar to the one used in the yaml_to_mux varianter plugin.

%files plugins-loader-yaml
%{python_sitelib}/avocado_loader_yaml*
%{python_sitelib}/avocado_framework_plugin_loader_yaml*

%package examples
Summary: Avocado Test Framework Example Tests
Requires: %{name} == %{version}

%description examples
The set of example tests present in the upstream tree of the Avocado framework.
Some of them are used as functional tests of the framework, others serve as
examples of how to write tests on your own.

%files examples
%{_datadir}/avocado/gdb-prerun-scripts
%{_datadir}/avocado/plugins
%{_datadir}/avocado/tests
%{_datadir}/avocado/wrappers
%{_datadir}/avocado/yaml_to_mux
%{_datadir}/avocado/yaml_to_mux_loader

%changelog
* Wed Sep 20 2017 Cleber Rosa <cleber@redhat.com> - 54.0-0
- New upstream release

* Tue Aug 22 2017 Cleber Rosa <cleber@redhat.com> - 53.0-1
- Use variable name for configuration dir
- Clean up old changelog entries
- Include other example files

* Tue Aug 15 2017 Cleber Rosa <cleber@redhat.com> - 53.0-0
- New upstream release

* Mon Aug 14 2017 Cleber Rosa <cleber@redhat.com> - 52.0-2
- Add python[2]-yaml requirements

* Tue Jun 27 2017 Cleber Rosa <cleber@redhat.com> - 52.0-1
- Fix python-aexpect depedency on EL7

* Mon Jun 26 2017 Cleber Rosa <cleber@redhat.com> - 52.0-0
- New upstream release
