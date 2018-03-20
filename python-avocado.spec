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
        %global commit      6c9fb563adf92581fb9368dff68c447bea4364a4
    %endif
    %if ! 0%{?commit_date:1}
        %global commit_date 20180424
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

%if 0%{?rhel}
%global with_python3 0
%else
%global with_python3 1
%endif

# The Python dependencies are already tracked by the python2
# or python3 "Requires".  This filters out the python binaries
# from the RPM automatic requires/provides scanner.
%global __requires_exclude ^/usr/bin/python[23]$

Summary: Framework with tools and libraries for Automated Testing
Name: python-%{srcname}
Version: 61.0
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
BuildRequires: kmod
%if 0%{?rhel} == 7
BuildRequires: pystache
BuildRequires: python-lxml
BuildRequires: python-setuptools
BuildRequires: python-stevedore
BuildRequires: python2-aexpect
BuildRequires: python2-devel
BuildRequires: python2-docutils
BuildRequires: python2-mock
BuildRequires: python2-psutil
BuildRequires: python2-requests
BuildRequires: python2-resultsdb_api
BuildRequires: python2-six
BuildRequires: python2-sphinx
BuildRequires: yum
%else
BuildRequires: pystache
BuildRequires: python2-aexpect
BuildRequires: python2-devel
BuildRequires: python2-docutils
BuildRequires: python2-lxml
BuildRequires: python2-mock
BuildRequires: python2-psutil
BuildRequires: python2-requests
BuildRequires: python2-resultsdb_api
BuildRequires: python2-setuptools
BuildRequires: python2-six
BuildRequires: python2-sphinx
BuildRequires: python2-stevedore
%endif

%if %{with_python3}
BuildRequires: python3-pystache
BuildRequires: python3-aexpect
BuildRequires: python3-devel
BuildRequires: python3-docutils
BuildRequires: python3-lxml
BuildRequires: python3-psutil
BuildRequires: python3-requests
BuildRequires: python3-setuptools
BuildRequires: python3-six
BuildRequires: python3-sphinx
BuildRequires: python3-stevedore
%endif

%if %{with_tests}
BuildRequires: libvirt-python
BuildRequires: perl-Test-Harness
%if 0%{?rhel}
BuildRequires: PyYAML
%else
BuildRequires: python2-yaml
%endif
%if %{with_python3}
BuildRequires: python3-yaml
%endif
%endif

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%package -n python2-%{srcname}
Summary: %{summary}
Requires: %{name}-common == %{version}
Requires: gdb
Requires: gdb-gdbserver
Requires: procps-ng
Requires: pyliblzma
%if 0%{?rhel} == 7
Requires: python
Requires: python-setuptools
Requires: python-six
Requires: python-stevedore
Requires: python2-requests
%else
Requires: python2
Requires: python2-requests
Requires: python2-setuptools
Requires: python2-six
Requires: python2-stevedore
%endif
%{?python_provide:%python_provide python2-%{srcname}}

%description -n python2-%{srcname}
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%if %{with_python3}
%package -n python3-%{srcname}
Summary: %{summary}
Requires: %{name}-common == %{version}
Requires: gdb
Requires: gdb-gdbserver
Requires: procps-ng
Requires: pyliblzma
Requires: python3
Requires: python3-requests
Requires: python3-setuptools
Requires: python3-six
Requires: python3-stevedore
%{?python_provide:%python_provide python3-%{srcname}}

%description -n python3-%{srcname}
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.
%endif

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
%if 0%{?rhel} == 7
sed -e "s/'six>=1.10.0'/'six>=1.9.0'/" -i setup.py
%endif
%py2_build
%if %{with_python3}
%py3_build
%endif
pushd optional_plugins/html
%py2_build
%if %{with_python3}
%py3_build
%endif
popd
# no runner_remote plugin on Python 3 due to missing Fabric package
pushd optional_plugins/runner_remote
%py2_build
popd
# no runner_vm plugin on Python 3 due to missing Fabric package
pushd optional_plugins/runner_vm
%py2_build
popd
# no runner_docker plugin on Python 3 due to missing Fabric package
pushd optional_plugins/runner_docker
%py2_build
popd
# no resultsdb plugin on Python 3 due to missing resultsdb_api package
pushd optional_plugins/resultsdb
%py2_build
popd
pushd optional_plugins/varianter_yaml_to_mux
%py2_build
%if %{with_python3}
%py3_build
%endif
popd
pushd optional_plugins/loader_yaml
%py2_build
%if %{with_python3}
%py3_build
%endif
popd
pushd optional_plugins/golang
%py2_build
%if %{with_python3}
%py3_build
%endif
popd
pushd optional_plugins/varianter_pict
%py2_build
%if %{with_python3}
%py3_build
%endif
popd
pushd optional_plugins/result_upload
%py2_build
%if %{with_python3}
%py3_build
%endif
popd
pushd optional_plugins/glib
%py2_build
%if %{with_python3}
%py3_build
%endif
popd
%{__make} man

%install
%py2_install
%{__mv} %{buildroot}%{python2_sitelib}/avocado/etc %{buildroot}
mv %{buildroot}%{_bindir}/avocado %{buildroot}%{_bindir}/avocado-%{python2_version}
ln -s avocado-%{python2_version} %{buildroot}%{_bindir}/avocado-2
%if %{with_python3}
%py3_install
mv %{buildroot}%{_bindir}/avocado %{buildroot}%{_bindir}/avocado-%{python3_version}
ln -s avocado-%{python3_version} %{buildroot}%{_bindir}/avocado-3
# configuration is held at /etc/avocado only and part of the
# python-avocado-common package
%{__rm} -rf %{buildroot}%{python3_sitelib}/avocado/etc
# ditto for libexec files
%{__rm} -rf %{buildroot}%{python3_sitelib}/avocado/libexec
%endif
ln -s avocado-%{python2_version} %{buildroot}%{_bindir}/avocado
pushd optional_plugins/html
%py2_install
%if %{with_python3}
%py3_install
%endif
popd
# no runner_remote plugin on Python 3 due to missing Fabric package
pushd optional_plugins/runner_remote
%py2_install
popd
# no runner_vm plugin on Python 3 due to missing Fabric package
pushd optional_plugins/runner_vm
%py2_install
popd
# no runner_docker plugin on Python 3 due to missing Fabric package
pushd optional_plugins/runner_docker
%py2_install
popd
# no resultsdb plugin on Python 3 due to missing resultsdb_api package
pushd optional_plugins/resultsdb
%py2_install
popd
pushd optional_plugins/varianter_yaml_to_mux
%py2_install
%if %{with_python3}
%py3_install
%endif
popd
pushd optional_plugins/loader_yaml
%py2_install
%if %{with_python3}
%py3_install
%endif
popd
pushd optional_plugins/golang
%py2_install
%if %{with_python3}
%py3_install
%endif
popd
pushd optional_plugins/varianter_pict
%py2_install
%if %{with_python3}
%py3_install
%endif
popd
pushd optional_plugins/result_upload
%py2_install
%if %{with_python3}
%py3_install
%endif
popd
pushd optional_plugins/glib
%py2_install
%if %{with_python3}
%py3_install
%endif
popd
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
%{__install} -m 0644 man/avocado-rest-client.1 %{buildroot}%{_mandir}/man1/avocado-rest-client.1
%{__install} -d -m 0755 %{buildroot}%{_sharedstatedir}/avocado/data
%{__install} -d -m 0755 %{buildroot}%{_datadir}/avocado
%{__cp} -r examples/gdb-prerun-scripts %{buildroot}%{_datadir}/avocado
%{__cp} -r examples/plugins %{buildroot}%{_datadir}/avocado
%{__cp} -r examples/tests %{buildroot}%{_datadir}/avocado
%{__cp} -r examples/wrappers %{buildroot}%{_datadir}/avocado
%{__cp} -r examples/yaml_to_mux %{buildroot}%{_datadir}/avocado
%{__cp} -r examples/yaml_to_mux_loader %{buildroot}%{_datadir}/avocado
%{__cp} -r examples/varianter_pict %{buildroot}%{_datadir}/avocado
%{__mkdir} -p %{buildroot}%{_libexecdir}/avocado
%{__mv} %{buildroot}%{python2_sitelib}/avocado/libexec/* %{buildroot}%{_libexecdir}/avocado

%check
%if %{with_tests}
%{__python2} setup.py develop --user
pushd optional_plugins/html
%{__python2} setup.py develop --user
popd
pushd optional_plugins/runner_remote
%{__python2} setup.py develop --user
popd
pushd optional_plugins/runner_vm
%{__python2} setup.py develop --user
popd
pushd optional_plugins/runner_docker
%{__python2} setup.py develop --user
popd
# no resultsdb plugin on Python 3 due to missing resultsdb_api package
pushd optional_plugins/resultsdb
%{__python2} setup.py develop --user
popd
pushd optional_plugins/varianter_yaml_to_mux
%{__python2} setup.py develop --user
popd
pushd optional_plugins/loader_yaml
%{__python2} setup.py develop --user
popd
pushd optional_plugins/golang
%{__python2} setup.py develop --user
popd
pushd optional_plugins/varianter_pict
%{__python2} setup.py develop --user
popd
pushd optional_plugins/result_upload
%{__python2} setup.py develop --user
popd
pushd optional_plugins/glib
%{__python2} setup.py develop --user
popd
# Package build environments have the least amount of resources
# we have observed so far.  Let's avoid tests that require too
# much resources or are time sensitive
LANG=en_US.UTF-8 AVOCADO_CHECK_LEVEL=0 %{__python2} selftests/run
%if %{with_python3}
%{__python3} setup.py develop --user
pushd optional_plugins/html
%{__python3} setup.py develop --user
popd
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
pushd optional_plugins/result_upload
%{__python3} setup.py develop --user
popd
pushd optional_plugins/glib
%{__python3} setup.py develop --user
popd
# Package build environments have the least amount of resources
# we have observed so far.  Let's avoid tests that require too
# much resources or are time sensitive
LANG=en_US.UTF-8 AVOCADO_CHECK_LEVEL=0 %{__python3} selftests/run
%endif
%endif

%files -n python2-%{srcname}
%defattr(-,root,root,-)
%doc README.rst LICENSE
%{python2_sitelib}/avocado*
%{_bindir}/avocado
%{_bindir}/avocado-2
%{_bindir}/avocado-%{python2_version}
%{_bindir}/avocado-rest-client
%{_mandir}/man1/avocado.1.gz
%{_mandir}/man1/avocado-rest-client.1.gz
%exclude %{python2_sitelib}/avocado_result_html*
%exclude %{python2_sitelib}/avocado_runner_remote*
%exclude %{python2_sitelib}/avocado_runner_vm*
%exclude %{python2_sitelib}/avocado_runner_docker*
%exclude %{python2_sitelib}/avocado_resultsdb*
%exclude %{python2_sitelib}/avocado_loader_yaml*
%exclude %{python2_sitelib}/avocado_golang*
%exclude %{python2_sitelib}/avocado_varianter_yaml_to_mux*
%exclude %{python2_sitelib}/avocado_varianter_pict*
%exclude %{python2_sitelib}/avocado_result_upload*
%exclude %{python2_sitelib}/avocado_glib*
%exclude %{python2_sitelib}/avocado_framework_plugin_result_html*
%exclude %{python2_sitelib}/avocado_framework_plugin_runner_remote*
%exclude %{python2_sitelib}/avocado_framework_plugin_runner_vm*
%exclude %{python2_sitelib}/avocado_framework_plugin_runner_docker*
%exclude %{python2_sitelib}/avocado_framework_plugin_resultsdb*
%exclude %{python2_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*
%exclude %{python2_sitelib}/avocado_framework_plugin_varianter_pict*
%exclude %{python2_sitelib}/avocado_framework_plugin_loader_yaml*
%exclude %{python2_sitelib}/avocado_framework_plugin_golang*
%exclude %{python2_sitelib}/avocado_framework_plugin_result_upload*
%exclude %{python2_sitelib}/avocado_framework_plugin_glib*
%exclude %{python2_sitelib}/avocado/libexec*
%exclude %{python2_sitelib}/tests*

%if %{with_python3}
%files -n python3-%{srcname}
%defattr(-,root,root,-)
%doc README.rst LICENSE
%{_bindir}/avocado-3
%{_bindir}/avocado-%{python3_version}
%{python3_sitelib}/avocado*
%exclude %{python3_sitelib}/avocado_result_html*
%exclude %{python3_sitelib}/avocado_loader_yaml*
%exclude %{python3_sitelib}/avocado_golang*
%exclude %{python3_sitelib}/avocado_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_varianter_pict*
%exclude %{python3_sitelib}/avocado_result_upload*
%exclude %{python3_sitelib}/avocado_glib*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_html*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_pict*
%exclude %{python3_sitelib}/avocado_framework_plugin_loader_yaml*
%exclude %{python3_sitelib}/avocado_framework_plugin_golang*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_upload*
%exclude %{python3_sitelib}/avocado_framework_plugin_glib*
%exclude %{python3_sitelib}/tests*
%endif

%package common
Summary: Avocado common files

%description common
Common files (such as configuration) for the Avocado Testing Framework.

%files common
%dir %{_sysconfdir}/avocado
%dir %{_sysconfdir}/avocado/conf.d
%dir %{_sysconfdir}/avocado/sysinfo
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

%package -n python2-%{srcname}-plugins-output-html
Summary: Avocado HTML report plugin
Requires: python2-%{srcname} == %{version}, pystache

%description -n python2-%{srcname}-plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files -n python2-%{srcname}-plugins-output-html
%{python2_sitelib}/avocado_result_html*
%{python2_sitelib}/avocado_framework_plugin_result_html*

%if %{with_python3}
%package -n python3-%{srcname}-plugins-output-html
Summary: Avocado HTML report plugin
Requires: python3-%{srcname} == %{version}, python3-pystache

%description -n python3-%{srcname}-plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files -n python3-%{srcname}-plugins-output-html
%{python3_sitelib}/avocado_result_html*
%{python3_sitelib}/avocado_framework_plugin_result_html*
%endif

%package -n python2-%{srcname}-plugins-runner-remote
Summary: Avocado Runner for Remote Execution
Requires: python2-%{srcname} == %{version}
Requires: fabric

%description -n python2-%{srcname}-plugins-runner-remote
Allows Avocado to run jobs on a remote machine, by means of an SSH
connection.  Avocado must be previously installed on the remote machine.

%files -n python2-%{srcname}-plugins-runner-remote
%{python2_sitelib}/avocado_runner_remote*
%{python2_sitelib}/avocado_framework_plugin_runner_remote*

%package -n python2-%{srcname}-plugins-runner-vm
Summary: Avocado Runner for libvirt VM Execution
Requires: python2-%{srcname} == %{version}
Requires: python2-%{srcname}-plugins-runner-remote == %{version}
Requires: libvirt-python

%description -n python2-%{srcname}-plugins-runner-vm
Allows Avocado to run jobs on a libvirt based VM, by means of
interaction with a libvirt daemon and an SSH connection to the VM
itself.  Avocado must be previously installed on the VM.

%files -n python2-%{srcname}-plugins-runner-vm
%{python2_sitelib}/avocado_runner_vm*
%{python2_sitelib}/avocado_framework_plugin_runner_vm*

%package -n python2-%{srcname}-plugins-runner-docker
Summary: Avocado Runner for Execution on Docker Containers
Requires: python2-%{srcname} == %{version}
Requires: python2-%{srcname}-plugins-runner-remote == %{version}
Requires: python2-aexpect

%description -n python2-%{srcname}-plugins-runner-docker
Allows Avocado to run jobs on a Docker container by interacting with a
Docker daemon and attaching to the container itself.  Avocado must
be previously installed on the container.

%files -n python2-%{srcname}-plugins-runner-docker
%{python2_sitelib}/avocado_runner_docker*
%{python2_sitelib}/avocado_framework_plugin_runner_docker*

%package -n python2-%{srcname}-plugins-resultsdb
Summary: Avocado plugin to propagate job results to ResultsDB
Requires: python2-%{srcname} == %{version}
Requires: python2-resultsdb_api

%description -n python2-%{srcname}-plugins-resultsdb
Allows Avocado to send job results directly to a ResultsDB
server.

%files -n python2-%{srcname}-plugins-resultsdb
%{python2_sitelib}/avocado_resultsdb*
%{python2_sitelib}/avocado_framework_plugin_resultsdb*
%config(noreplace)%{_sysconfdir}/avocado/conf.d/resultsdb.conf

%package -n python2-%{srcname}-plugins-varianter-yaml-to-mux
Summary: Avocado plugin to generate variants out of yaml files
Requires: python2-%{srcname} == %{version}
%if 0%{?rhel}
Requires: PyYAML
%else
Requires: python2-yaml
%endif

%description -n python2-%{srcname}-plugins-varianter-yaml-to-mux
Can be used to produce multiple test variants with test parameters
defined in a yaml file(s).

%files -n python2-%{srcname}-plugins-varianter-yaml-to-mux
%{python2_sitelib}/avocado_varianter_yaml_to_mux*
%{python2_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*

%if %{with_python3}
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
%endif

%package -n python2-%{srcname}-plugins-loader-yaml
Summary: Avocado Plugin that loads tests from YAML files
Requires: python2-%{srcname}-plugins-varianter-yaml-to-mux == %{version}

%description -n python2-%{srcname}-plugins-loader-yaml
Can be used to produce a test suite from definitions in a YAML file,
similar to the one used in the yaml_to_mux varianter plugin.

%files -n python2-%{srcname}-plugins-loader-yaml
%{python2_sitelib}/avocado_loader_yaml*
%{python2_sitelib}/avocado_framework_plugin_loader_yaml*

%if %{with_python3}
%package -n python3-%{srcname}-plugins-loader-yaml
Summary: Avocado Plugin that loads tests from YAML files
Requires: python3-%{srcname}-plugins-varianter-yaml-to-mux == %{version}

%description -n python3-%{srcname}-plugins-loader-yaml
Can be used to produce a test suite from definitions in a YAML file,
similar to the one used in the yaml_to_mux varianter plugin.

%files -n python3-%{srcname}-plugins-loader-yaml
%{python3_sitelib}/avocado_loader_yaml*
%{python3_sitelib}/avocado_framework_plugin_loader_yaml*
%endif

%package -n python2-%{srcname}-plugins-golang
Summary: Avocado Plugin for Execution of golang tests
Requires: python2-%{srcname} == %{version}
Requires: golang

%description -n python2-%{srcname}-plugins-golang
Allows Avocado to list golang tests, and if golang is installed,
also run them.

%files -n python2-%{srcname}-plugins-golang
%{python2_sitelib}/avocado_golang*
%{python2_sitelib}/avocado_framework_plugin_golang*

%if %{with_python3}
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
%endif

%package -n python2-%{srcname}-plugins-varianter-pict
Summary: Varianter with combinatorial capabilities by PICT
Requires: python2-%{srcname} == %{version}

%description -n python2-%{srcname}-plugins-varianter-pict
This plugin uses a third-party tool to provide variants created by
Pair-Wise algorithms, also known as Combinatorial Independent Testing.

%files -n python2-%{srcname}-plugins-varianter-pict
%{python2_sitelib}/avocado_varianter_pict*
%{python2_sitelib}/avocado_framework_plugin_varianter_pict*

%if %{with_python3}
%package -n python3-%{srcname}-plugins-varianter-pict
Summary: Varianter with combinatorial capabilities by PICT
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-plugins-varianter-pict
This plugin uses a third-party tool to provide variants created by
Pair-Wise algorithms, also known as Combinatorial Independent Testing.

%files -n python3-%{srcname}-plugins-varianter-pict
%{python3_sitelib}/avocado_varianter_pict*
%{python3_sitelib}/avocado_framework_plugin_varianter_pict*
%endif

%package -n python2-%{srcname}-plugins-result-upload
Summary: Avocado Plugin to propagate Job results to a remote host
Requires: python2-%{srcname} == %{version}

%description -n python2-%{srcname}-plugins-result-upload
This optional plugin is intended to upload the Avocado Job results to
a dedicated sever.

%files -n python2-%{srcname}-plugins-result-upload
%{python2_sitelib}/avocado_result_upload*
%{python2_sitelib}/avocado_framework_plugin_result_upload*
%config(noreplace)%{_sysconfdir}/avocado/conf.d/result_upload.conf

%if %{with_python3}
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
%endif

%package -n python2-%{srcname}-plugins-glib
Summary: Avocado Plugin for Execution of GLib Test Framework tests
Requires: python2-%{srcname} == %{version}

%description -n python2-%{srcname}-plugins-glib
This optional plugin is intended to list and run tests written in the
GLib Test Framework.

%files -n python2-%{srcname}-plugins-glib
%{python2_sitelib}/avocado_glib*
%{python2_sitelib}/avocado_framework_plugin_glib*

%if %{with_python3}
%package -n python3-%{srcname}-plugins-glib
Summary: Avocado Plugin for Execution of GLib Test Framework tests
Requires: python3-%{srcname} == %{version}

%description -n python3-%{srcname}-plugins-glib
This optional plugin is intended to list and run tests written in the
GLib Test Framework.

%files -n python3-%{srcname}-plugins-glib
%{python3_sitelib}/avocado_glib*
%{python3_sitelib}/avocado_framework_plugin_glib*
%endif

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
%{_datadir}/avocado/varianter_pict

%package bash
Summary: Avocado Test Framework Bash Utilities
Requires: %{name} == %{version}

%description bash
A small set of utilities to interact with Avocado from the Bourne
Again Shell code (and possibly other similar shells).

%files bash
%{_libexecdir}/avocado*

%changelog
* Tue Apr 24 2018 Cleber Rosa <cleber@redhat.com> - 61.0-0
- New release
- Added python3-yaml require to varianter-yaml-to-mux package
- Force a locale with utf-8 encoding to run tests

* Wed Apr  4 2018 Cleber Rosa <cleber@redhat.com> - 60.0-2
- Moved all requirements to python2-avocado and python3-avocado
- Added python_provides macro on Python 3 package
- Filter out python binaries from requirements
- Added explicit six requirement on Python 2 packages

* Wed Mar 28 2018 Cleber Rosa <cleber@redhat.com> - 60.0-1
- Moved "common" dep into python2-avocado and python3-avocado

* Wed Mar 28 2018 Cleber Rosa <cleber@redhat.com> - 60.0-0
- New release

* Mon Mar 19 2018 Cleber Rosa <cleber@redhat.com> - 59.0-2
- Removed backward compatibility with name avocado on plugins
- Removed extra dependencies on Fedora 24 for runner-remote
- Added python-avocado requirement for golang plugin
- Added new common sub-package
- Make bash package independent of Python version
- Set supported Python major version explicitly to 2
- Added Python 3 packages

* Thu Mar  8 2018 Cleber Rosa <cleber@redhat.com> - 59.0-1
- Remove backward compatibility with name avocado
- Remove hack to workaround fabric bugs on Fedora 24
- Use real package name for python YAML package on EL
- Use exact package names on requires
- Remove unecessary conditional for kmod

* Wed Feb 28 2018 Cleber Rosa <cleber@redhat.com> - 59.0-0
- New upstream release
- Added glib plugin subpackage

* Tue Jan 23 2018 Cleber Rosa <cleber@redhat.com> - 58.0-1
- Require a lower six version on EL7

* Tue Jan 23 2018 Cleber Rosa <cleber@redhat.com> - 58.0-0
- New upstream release

* Sat Jan  6 2018 Cleber Rosa <cleber@redhat.com> - 57.0-3
- Move the avocado package config files to the system location
- Add missing configuration files for sub packages
- Adapt to change in example file installation
- Remove man pages source files from package
- Add bash subpackage

* Tue Dec 19 2017 Cleber Rosa <cleber@redhat.com> - 57.0-2
- Removed patch added on release 1, considering it's upstream

* Tue Dec 19 2017 Cleber Rosa <cleber@redhat.com> - 57.0-1
- Add patch to skip tests on EPEL 7 due to mock version

* Tue Dec 19 2017 Cleber Rosa <cleber@redhat.com> - 57.0-0
- New upstream release

* Fri Dec 15 2017 Cleber Rosa <cleber@redhat.com> - 56.0-1
- Added result_upload plugin

* Tue Nov 21 2017 Cleber Rosa <cleber@redhat.com> - 56.0-0
- New upstream release

* Thu Nov 16 2017 Cleber Rosa <cleber@redhat.com> - 55.0-1
- Introduced sub-package plugins-varianter-pict

* Tue Oct 17 2017 Cleber Rosa <cleber@redhat.com> - 55.0-0
- New upstream release

* Mon Oct 16 2017 Cleber Rosa <cleber@redhat.com> - 54.1-3
- Excluded avocado_loader_yaml files from main package
- Package recently introduced golang plugin

* Wed Oct  4 2017 Cleber Rosa <cleber@redhat.com> - 54.1-2
- Remove python-flexmock requirement

* Wed Oct  4 2017 Cleber Rosa <cleber@redhat.com> - 54.1-1
- Add explicit BuildRequires for python-six

* Wed Sep 20 2017 Cleber Rosa <cleber@redhat.com> - 54.1-0
- New minor upstream release

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
