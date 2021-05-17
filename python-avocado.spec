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
        %global commit      87d40d3e84b505e8e7c56912d62910d084aa9d3d
    %endif
    %if ! 0%{?commit_date:1}
        %global commit_date 20210517
    %endif
    %global shortcommit     %(c=%{commit};echo ${c:0:9})
    %global gitrel          .%{commit_date}git%{shortcommit}
    %global gittar          %{srcname}-%{shortcommit}.tar.gz
%endif

# Selftests are provided but may need to be skipped because many of
# the functional tests are time and resource sensitive and can
# cause race conditions and random build failures. They are
# enabled by default.
%global with_tests 1

# The Python dependencies are already tracked by the python2
# or python3 "Requires".  This filters out the python binaries
# from the RPM automatic requires/provides scanner.
%global __requires_exclude ^/usr/bin/python[23]$

Summary: Framework with tools and libraries for Automated Testing
Name: python-%{srcname}
Version: 88.1
Release: 1%{?gitrel}%{?dist}
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
%if 0%{?fedora} >= 30
BuildRequires: glibc-all-langpacks
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
%if 0%{?rhel}
sed -e "s/'PyYAML>=4.2b2'/'PyYAML>=3.12'/" -i optional_plugins/varianter_yaml_to_mux/setup.py
%endif
%if 0%{?rhel}
%endif
%py3_build
pushd optional_plugins/html
%py3_build
popd
%if ! 0%{?rhel}
pushd optional_plugins/resultsdb
%py3_build
popd
%endif
pushd optional_plugins/varianter_yaml_to_mux
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
rst2man man/avocado.rst man/avocado.1

%install
%py3_install
%{__mv} %{buildroot}%{python3_sitelib}/avocado/etc %{buildroot}
pushd optional_plugins/html
%py3_install
popd
%if ! 0%{?rhel}
pushd optional_plugins/resultsdb
%py3_install
popd
%endif
pushd optional_plugins/varianter_yaml_to_mux
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
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
%{__install} -d -m 0755 %{buildroot}%{_sharedstatedir}/avocado/data
%{__install} -d -m 0755 %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/gdb-prerun-scripts %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/plugins %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/tests %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/wrappers %{buildroot}%{_docdir}/avocado
%{__cp} -r examples/yaml_to_mux %{buildroot}%{_docdir}/avocado
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
%if ! 0%{?rhel}
pushd optional_plugins/resultsdb
%{__python3} setup.py develop --user
popd
%endif
pushd optional_plugins/varianter_yaml_to_mux
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
# LANG: to make the results predictable, we pin the language
# that is used during test execution.
# AVOCADO_CHECK_LEVEL: package build environments have the least
# amount of resources we have observed so far.  Let's avoid tests that
# require too much resources or are time sensitive
PATH=$HOME/.local/bin:$PATH LANG=en_US.UTF-8 AVOCADO_CHECK_LEVEL=0 %{__python3} selftests/check.py --disable-static-checks --disable-plugin-checks=robot
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
%{_bindir}/avocado-runner-tap
%{_bindir}/avocado-runner-requirement-package
%{_bindir}/avocado-software-manager
%{python3_sitelib}/avocado*
%exclude %{python3_sitelib}/avocado_result_html*
%exclude %{python3_sitelib}/avocado_resultsdb*
%exclude %{python3_sitelib}/avocado_golang*
%exclude %{python3_sitelib}/avocado_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_varianter_pict*
%exclude %{python3_sitelib}/avocado_varianter_cit*
%exclude %{python3_sitelib}/avocado_result_upload*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_html*
%exclude %{python3_sitelib}/avocado_framework_plugin_resultsdb*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_pict*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_cit*
%exclude %{python3_sitelib}/avocado_framework_plugin_golang*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_upload*
%exclude %{python3_sitelib}/tests*

%package -n python3-%{srcname}-common
Summary: Avocado common files

%description -n python3-%{srcname}-common
Common files (such as configuration) for the Avocado Testing Framework.

%files -n python3-%{srcname}-common
%{_mandir}/man1/avocado.1.gz
%dir %{_sysconfdir}/avocado
%dir %{_sysconfdir}/avocado/sysinfo
%dir %{_sysconfdir}/avocado/scripts
%dir %{_sysconfdir}/avocado/scripts/job
%dir %{_sysconfdir}/avocado/scripts/job/pre.d
%dir %{_sysconfdir}/avocado/scripts/job/post.d
%dir %{_sharedstatedir}/avocado
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
%{_bindir}/avocado-runner-golang

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
* Mon May 17 2021 Cleber Rosa <cleber@redhat.com> - 88.1-1
- New release with readthedocs.org documentation hotfix

* Fri May 14 2021 Cleber Rosa <cleber@redhat.com> - 88.0-1
- New release

* Wed Apr 14 2021 Cleber Rosa <cleber@redhat.com> - 87.0-1
- New release

* Mon Mar 15 2021 Cleber Rosa <cleber@redhat.com> - 86.0-1
- New release

* Thu Feb 18 2021 Cleber Rosa <cleber@redhat.com> - 85.0-2
- Do not depend on make to build man page

* Tue Feb  9 2021 Cleber Rosa <cleber@redhat.com> - 85.0-1
- New release

* Mon Dec 21 2020 Cleber Rosa <cleber@redhat.com> - 84.0-1
- New release

* Tue Dec  8 2020 Cleber Rosa <cleber@redhat.com> - 83.0-2
- Drop old Fedora conditionals
- Use selftests/check.py job instead of more limited selftests/run

* Mon Nov 16 2020 Cleber Rosa <cleber@redhat.com> - 83.0-1
- New release

* Thu Sep 17 2020 Cleber Rosa <cleber@redhat.com> - 82.0-3
- Added avocado-runner-golang script to golang package

* Wed Sep 16 2020 Cleber Rosa <cleber@redhat.com> - 82.0-2
- Removed yaml to mux loader plugin
- Removed glib plugin

* Fri Sep 11 2020 Cleber Rosa <cleber@redhat.com> - 82.0-1
- New release

* Mon Aug 31 2020 Cleber Rosa <cleber@redhat.com> - 81.0-1
- New release

* Tue Jun 23 2020 Cleber Rosa <cleber@redhat.com> - 80.0-2
- Add on extra character to short commit

* Fri Jun  5 2020 Cleber Rosa <cleber@redhat.com> - 80.0-2
- Removed python3-libvirt build requirement

* Fri Jun  5 2020 Cleber Rosa <cleber@redhat.com> - 80.0-1
- New release

* Thu Jun  4 2020 Cleber Rosa <cleber@redhat.com> - 79.0-2
- Dropped use of custom avocado command for tests

* Tue May 12 2020 Cleber Rosa <cleber@redhat.com> - 79.0-1
- Do not build deprecated runners

* Mon May 11 2020 Cleber Rosa <cleber@redhat.com> - 79.0-0
- New release
- Added current user's ~/local/.bin to the PATH environment variable
  while running tests, so that avocado-runner-* scripts can be found
- Moved comment to new lines closing the conditionals, to avoid
  errors from rpmlint and rpmbuild

* Mon Apr 13 2020 Cleber Rosa <cleber@redhat.com> - 78.0-0
- New release

* Tue Mar 17 2020 Cleber Rosa <cleber@redhat.com> - 77.0-0
- New release

* Mon Mar 16 2020 Cleber Rosa <cleber@redhat.com> - 76.0-1
- Removed PYTHONWARNINGS environment variable when running tests

* Fri Feb 21 2020 Cleber Rosa <cleber@redhat.com> - 76.0-0
- New release

* Thu Feb 20 2020 Cleber Rosa <cleber@redhat.com> - 75.1-3
- Added new avocado-software-manager script

* Thu Feb 20 2020 Cleber Rosa <cleber@redhat.com> - 75.1-2
- Added new avocado-runner-tap script

* Thu Feb 20 2020 Cleber Rosa <cleber@redhat.com> - 75.1-1
- Ignore Avocado warnings that use Python's warning module when
  running tests

* Mon Jan 20 2020 Cleber Rosa <cleber@redhat.com> - 75.1-0
- New release

* Mon Jan 20 2020 Cleber Rosa <cleber@redhat.com> - 75.0-0
- New release

* Sun Dec 22 2019 Cleber Rosa <cleber@redhat.com> - 74.0-0
- New release

* Fri Nov 22 2019 Cleber Rosa <cleber@redhat.com> - 73.0-0
- New release

* Fri Nov 22 2019 Cleber Rosa <cleber@redhat.com> - 72.0-3
- Update sysinfo configuration files location

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
