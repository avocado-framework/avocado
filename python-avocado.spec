# Conditional for release vs. snapshot builds. Set to 1 for release build.
%if ! 0%{?rel_build:1}
    %global rel_build 1
%endif

# Settings used for build from snapshots.
%if 0%{?rel_build}
    %global gittar          avocado-%{version}.tar.gz
%else
    %if ! 0%{?commit:1}
        %global commit      a74bc734330c9c9f2b91df4e796c4422ac57b918
    %endif
    %if ! 0%{?commit_date:1}
        %global commit_date 20211019
    %endif
    %global shortcommit     %(c=%{commit};echo ${c:0:9})
    %global gitrel          .%{commit_date}git%{shortcommit}
    %global gittar          avocado-%{shortcommit}.tar.gz
%endif

# Selftests are provided but may need to be skipped because many of
# the functional tests are time and resource sensitive and can
# cause race conditions and random build failures. They are
# enabled by default.
# You can disable them with rpmbuild ... --without tests
%bcond_without tests

Summary: Framework with tools and libraries for Automated Testing
Name: python-avocado
Version: 107.0
Release: 1%{?gitrel}%{?dist}
License: GPLv2+ and GPLv2 and MIT
URL: https://avocado-framework.github.io/
%if 0%{?rel_build}
Source0: https://github.com/avocado-framework/avocado/archive/%{version}/%{gittar}
%else
Source0: https://github.com/avocado-framework/avocado/archive/%{commit}/%{gittar}
%endif
BuildArch: noarch
BuildRequires: procps-ng
BuildRequires: kmod
BuildRequires: glibc-all-langpacks
BuildRequires: python3-jinja2
BuildRequires: python3-devel
BuildRequires: python3-docutils
BuildRequires: python3-lxml
BuildRequires: python3-psutil
BuildRequires: python3-setuptools
%if ! 0%{?rhel}
BuildRequires: python3-aexpect
%endif

%if ! 0%{?rhel}
%if ! 0%{?fedora} > 35
BuildRequires: python3-resultsdb_api
%endif
BuildRequires: python3-pycdlib
BuildRequires: ansible-core
%endif

%if %{with tests}
BuildRequires: python3-jsonschema
%if ! 0%{?rhel} >= 9
BuildRequires: genisoimage
%endif
BuildRequires: libcdio
BuildRequires: psmisc
BuildRequires: python3-yaml
BuildRequires: python3-netifaces
%if ! 0%{?rhel}
BuildRequires: perl-Test-Harness
BuildRequires: python3-xmlschema
%endif
BuildRequires: zstd
%endif

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%package -n python3-avocado
Summary: %{summary}
Requires: python3-avocado-common == %{version}-%{release}
Requires: gdb
Requires: gdb-gdbserver
Requires: procps-ng
Requires: python3-jsonschema
%if ! 0%{?rhel}
Requires: python3-pycdlib
%endif

%description -n python3-avocado
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%prep
%if 0%{?rel_build}
%setup -q -n avocado-%{version}
%else
%setup -q -n avocado-%{commit}
%endif

%build
%if 0%{?rhel}
sed -e 's/"PyYAML>=4.2b2"/"PyYAML>=3.12"/' -i optional_plugins/varianter_yaml_to_mux/setup.py
%endif
%py3_build
pushd optional_plugins/html
%py3_build
popd
%if ! 0%{?rhel}
%if ! 0%{?fedora} > 35
pushd optional_plugins/resultsdb
%py3_build
popd
%endif
%endif
pushd optional_plugins/varianter_yaml_to_mux
%py3_build
popd
pushd optional_plugins/golang
%py3_build
popd
%if ! 0%{?rhel}
pushd optional_plugins/ansible
%py3_build
popd
%endif
pushd optional_plugins/varianter_pict
%py3_build
popd
pushd optional_plugins/varianter_cit
%py3_build
popd
pushd optional_plugins/result_upload
%py3_build
popd
pushd optional_plugins/mail
%py3_build
popd
%if ! 0%{?rhel}
pushd optional_plugins/spawner_remote
%py3_build
popd
%endif
rst2man man/avocado.rst man/avocado.1

%install
%py3_install
mv %{buildroot}%{python3_sitelib}/avocado/etc %{buildroot}
pushd optional_plugins/html
%py3_install
popd
%if ! 0%{?rhel}
%if ! 0%{?fedora} > 35
pushd optional_plugins/resultsdb
%py3_install
popd
%endif
%endif
pushd optional_plugins/varianter_yaml_to_mux
%py3_install
popd
pushd optional_plugins/golang
%py3_install
popd
%if ! 0%{?rhel}
pushd optional_plugins/ansible
%py3_install
popd
%endif
pushd optional_plugins/varianter_pict
%py3_install
popd
pushd optional_plugins/varianter_cit
%py3_install
popd
pushd optional_plugins/result_upload
%py3_install
popd
pushd optional_plugins/mail
%py3_install
popd
%if ! 0%{?rhel}
pushd optional_plugins/spawner_remote
%py3_install
popd
%endif
mkdir -p %{buildroot}%{_mandir}/man1
install -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
mkdir -p %{buildroot}%{_pkgdocdir}
install -m 0644 README.rst %{buildroot}%{_pkgdocdir}
install -d -m 0755 %{buildroot}%{_sharedstatedir}/avocado/data
install -d -m 0755 %{buildroot}%{_docdir}/avocado
cp -r examples/gdb-prerun-scripts %{buildroot}%{_docdir}/avocado
cp -r examples/plugins %{buildroot}%{_docdir}/avocado
cp -r examples/tests %{buildroot}%{_docdir}/avocado
cp -r examples/yaml_to_mux %{buildroot}%{_docdir}/avocado
cp -r examples/varianter_pict %{buildroot}%{_docdir}/avocado
cp -r examples/varianter_cit %{buildroot}%{_docdir}/avocado
mkdir -p %{buildroot}%{_datarootdir}/avocado
mv %{buildroot}%{python3_sitelib}/avocado/schemas %{buildroot}%{_datarootdir}/avocado
find %{buildroot}%{_docdir}/avocado -type f -name '*.py' -exec chmod -c -x {} ';'
mkdir -p %{buildroot}%{_libexecdir}/avocado
mv %{buildroot}%{python3_sitelib}/avocado/libexec/* %{buildroot}%{_libexecdir}/avocado
rmdir %{buildroot}%{python3_sitelib}/avocado/libexec

%if %{with tests}
%check
# LANG: to make the results predictable, we pin the language
# that is used during test execution.
# AVOCADO_CHECK_LEVEL: package build environments have the least
# amount of resources we have observed so far.  Let's avoid tests that
# require too much resources or are time sensitive
PATH=%{buildroot}%{_bindir}:%{buildroot}%{_libexecdir}/avocado:$PATH \
    PYTHONPATH=%{buildroot}%{python3_sitelib}:. \
    LANG=en_US.UTF-8 \
    AVOCADO_CHECK_LEVEL=0 \
    %{python3} selftests/check.py --skip static-checks --disable-plugin-checks robot
%endif

%files -n python3-avocado
%defattr(-,root,root,-)
%license LICENSE
%{_pkgdocdir}/README.rst
%{_bindir}/avocado
%{_bindir}/avocado-runner-noop
%{_bindir}/avocado-runner-dry-run
%{_bindir}/avocado-runner-exec-test
%{_bindir}/avocado-runner-python-unittest
%{_bindir}/avocado-runner-avocado-instrumented
%{_bindir}/avocado-runner-tap
%{_bindir}/avocado-runner-asset
%{_bindir}/avocado-runner-package
%{_bindir}/avocado-runner-podman-image
%{_bindir}/avocado-runner-sysinfo
%{_bindir}/avocado-software-manager
%{_bindir}/avocado-external-runner
%{python3_sitelib}/avocado*
%exclude %{python3_sitelib}/avocado_result_html*
%exclude %{python3_sitelib}/avocado_resultsdb*
%exclude %{python3_sitelib}/avocado_golang*
%exclude %{python3_sitelib}/avocado_ansible*
%exclude %{python3_sitelib}/avocado_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_varianter_pict*
%exclude %{python3_sitelib}/avocado_varianter_cit*
%exclude %{python3_sitelib}/avocado_result_upload*
%exclude %{python3_sitelib}/avocado_result_mail*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_html*
%exclude %{python3_sitelib}/avocado_framework_plugin_resultsdb*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_pict*
%exclude %{python3_sitelib}/avocado_framework_plugin_varianter_cit*
%exclude %{python3_sitelib}/avocado_framework_plugin_golang*
%exclude %{python3_sitelib}/avocado_framework_plugin_ansible*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_upload*
%exclude %{python3_sitelib}/avocado_framework_plugin_result_mail*
%exclude %{python3_sitelib}/avocado_framework_plugin_spawner_remote*
%exclude %{python3_sitelib}/tests*

%package -n python3-avocado-common
Summary: Avocado common files
License: GPLv2+

%description -n python3-avocado-common
Common files (such as configuration) for the Avocado Testing Framework.

%files -n python3-avocado-common
%license LICENSE
%{_mandir}/man1/avocado.1.gz
%dir %{_sysconfdir}/avocado
%dir %{_sysconfdir}/avocado/sysinfo
%dir %{_sysconfdir}/avocado/scripts
%dir %{_sysconfdir}/avocado/scripts/job
%dir %{_sysconfdir}/avocado/scripts/job/pre.d
%dir %{_sysconfdir}/avocado/scripts/job/post.d
%dir %{_sharedstatedir}/avocado
%dir %{_sharedstatedir}/avocado/data
%dir %{_datarootdir}/avocado
%dir %{_datarootdir}/avocado/schemas
%{_datarootdir}/avocado/schemas/*
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/commands
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/files
%config(noreplace)%{_sysconfdir}/avocado/sysinfo/profilers
%config(noreplace)%{_sysconfdir}/avocado/scripts/job/pre.d/README
%config(noreplace)%{_sysconfdir}/avocado/scripts/job/post.d/README

%package -n python3-avocado-plugins-output-html
Summary: Avocado HTML report plugin
License: GPLv2+ and MIT
Requires: python3-avocado == %{version}-%{release}
Requires: python3-jinja2

%description -n python3-avocado-plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files -n python3-avocado-plugins-output-html
%{python3_sitelib}/avocado_result_html*
%{python3_sitelib}/avocado_framework_plugin_result_html*

%if ! 0%{?rhel}
%if ! 0%{?fedora} > 35
%package -n python3-avocado-plugins-resultsdb
Summary: Avocado plugin to propagate job results to ResultsDB
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}
Requires: python3-resultsdb_api

%description -n python3-avocado-plugins-resultsdb
Allows Avocado to send job results directly to a ResultsDB
server.

%files -n python3-avocado-plugins-resultsdb
%{python3_sitelib}/avocado_resultsdb*
%{python3_sitelib}/avocado_framework_plugin_resultsdb*
%endif
%endif

%package -n python3-avocado-plugins-varianter-yaml-to-mux
Summary: Avocado plugin to generate variants out of yaml files
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}
Requires: python3-yaml

%description -n python3-avocado-plugins-varianter-yaml-to-mux
Can be used to produce multiple test variants with test parameters
defined in a yaml file(s).

%files -n python3-avocado-plugins-varianter-yaml-to-mux
%{python3_sitelib}/avocado_varianter_yaml_to_mux*
%{python3_sitelib}/avocado_framework_plugin_varianter_yaml_to_mux*

%package -n python3-avocado-plugins-golang
Summary: Avocado Plugin for Execution of golang tests
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}
Requires: golang

%description -n python3-avocado-plugins-golang
Allows Avocado to list golang tests, and if golang is installed,
also run them.

%files -n python3-avocado-plugins-golang
%{python3_sitelib}/avocado_golang*
%{python3_sitelib}/avocado_framework_plugin_golang*
%{_bindir}/avocado-runner-golang

%if ! 0%{?rhel}
%package -n python3-avocado-plugins-ansible
Summary: Avocado Ansible Dependency plugin
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}
Requires: ansible-core

%description -n python3-avocado-plugins-ansible
Adds to Avocado the ability to use ansible modules as dependencies for
tests.

%files -n python3-avocado-plugins-ansible
%{python3_sitelib}/avocado_ansible*
%{python3_sitelib}/avocado_framework_plugin_ansible*
%{_bindir}/avocado-runner-ansible-module
%endif

%package -n python3-avocado-plugins-varianter-pict
Summary: Varianter with combinatorial capabilities by PICT
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}

%description -n python3-avocado-plugins-varianter-pict
This plugin uses a third-party tool to provide variants created by
Pair-Wise algorithms, also known as Combinatorial Independent Testing.

%files -n python3-avocado-plugins-varianter-pict
%{python3_sitelib}/avocado_varianter_pict*
%{python3_sitelib}/avocado_framework_plugin_varianter_pict*

%package -n python3-avocado-plugins-varianter-cit
Summary: Varianter with Combinatorial Independent Testing capabilities
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}

%description -n python3-avocado-plugins-varianter-cit
A varianter plugin that generates variants using Combinatorial
Independent Testing (AKA Pair-Wise) algorithm developed in
collaboration with CVUT Prague.

%files -n python3-avocado-plugins-varianter-cit
%{python3_sitelib}/avocado_varianter_cit*
%{python3_sitelib}/avocado_framework_plugin_varianter_cit*

%package -n python3-avocado-plugins-result-upload
Summary: Avocado Plugin to propagate Job results to a remote host
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}

%description -n python3-avocado-plugins-result-upload
This optional plugin is intended to upload the Avocado Job results to
a dedicated sever.

%files -n python3-avocado-plugins-result-upload
%{python3_sitelib}/avocado_result_upload*
%{python3_sitelib}/avocado_framework_plugin_result_upload*

%package -n python3-avocado-plugins-result-mail
Summary: Avocado Mail Notification for Jobs
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}

%description -n python3-avocado-plugins-result-mail
The Mail result plugin enables you to receive email notifications
for job start and completion events within the Avocado testing framework.

%files -n python3-avocado-plugins-result-mail
%{python3_sitelib}/avocado_result_mail*
%{python3_sitelib}/avocado_framework_plugin_result_mail*

%if ! 0%{?rhel}
%package -n python3-avocado-plugins-spawner-remote
Summary: Avocado Plugin to spawn tests on a remote host
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}

%description -n python3-avocado-plugins-spawner-remote
This optional plugin is intended to spawn tests on a remote host.

%files -n python3-avocado-plugins-spawner-remote
%{python3_sitelib}/avocado_spawner_remote*
%{python3_sitelib}/avocado_framework_plugin_spawner_remote*
%endif

%package -n python3-avocado-examples
Summary: Avocado Test Framework Example Tests
License: GPLv2+
Requires: python3-avocado == %{version}-%{release}

%description -n python3-avocado-examples
The set of example tests present in the upstream tree of the Avocado framework.
Some of them are used as functional tests of the framework, others serve as
examples of how to write tests on your own.

%files -n python3-avocado-examples
%license LICENSE
%dir %{_docdir}/avocado
%{_docdir}/avocado/gdb-prerun-scripts
%{_docdir}/avocado/plugins
%{_docdir}/avocado/tests
%{_docdir}/avocado/yaml_to_mux
%{_docdir}/avocado/varianter_pict
%{_docdir}/avocado/varianter_cit

%package -n python3-avocado-bash
Summary: Avocado Test Framework Bash Utilities
License: GPLv2+ and GPLv2
Requires: python3-avocado == %{version}-%{release}

%description -n python3-avocado-bash
A small set of utilities to interact with Avocado from the Bourne
Again Shell code (and possibly other similar shells).

%files -n python3-avocado-bash
%license LICENSE
%{_libexecdir}/avocado*

%changelog
* Mon Sep 02 2024 Cleber Rosa <crosa@redhat.com> - 107.0-1
- New release

* Sat Jun 29 2024 Cleber Rosa <crosa@redhat.com> - 106.0-1
- New release

* Tue May 07 2024 Cleber Rosa <crosa@redhat.com> - 105.0-1
- New release

* Tue Apr  2 2024 Cleber Rosa <crosa@redhat.com> - 104.0-2
- Package JSON schema files
- Removed empty libexec dir
- Require python3-jsonschema to perform runtime schema validation
  for recipe files

* Tue Mar 19 2024 Jan Richter <jarichte@redhat.com> - 104.0-1
- New release

* Sat Jan 06 2024 Cleber Rosa <crosa@redhat.com> - 103.0-1
- New release

* Tue Jul 18 2023 Cleber Rosa <crosa@redhat.com> - 102.0-2
- Removed python3-elementpath build requirement

* Fri Jun 23 2023 Cleber Rosa <crosa@redhat.com> - 102.0-1
- New release

* Fri Mar 10 2023 Cleber Rosa <crosa@redhat.com> - 101.0-1
- New release

* Tue Feb 14 2023 Cleber Rosa <crosa@redhat.com> - 100.1-2
- Added zstd to build requirements

* Thu Jan 19 2023 Cleber Rosa <crosa@redhat.com> - 100.1-1
- New release

* Fri Jan 13 2023 Cleber Rosa <crosa@redhat.com> - 100.0-1
- New release

* Sun Nov 20 2022 Cleber Rosa <crosa@redhat.com> - 99.0-1
- Remove generic runner avocado-runner

* Thu Nov 10 2022 Cleber Rosa <crosa@redhat.com> - 99.0-1
- New release

* Mon Jul 25 2022 Cleber Rosa <crosa@redhat.com> - 98.0-3
- Added new sub package python3-avocado-plugins-ansible

* Thu Jul 21 2022 Cleber Rosa <crosa@redhat.com> - 98.0-2
- Added new avocado-runner-podman-image script

* Thu Jul 14 2022 Cleber Rosa <crosa@redhat.com> - 98.0-1
- New release

* Thu Jul  7 2022 Cleber Rosa <crosa@redhat.com> - 97.0-2
- Add build requirements for python3-elementpath and
  python3-xmlschema, used on some tests

* Tue May 24 2022 Cleber Rosa <crosa@redhat.com> - 97.0-1
- New release

* Fri Apr 29 2022 Cleber Rosa <crosa@redhat.com> - 96.0-3
- Require python3-jsonschema when running tests

* Wed Apr 27 2022 Cleber Rosa <crosa@redhat.com> - 96.0-2
- Removed wrapper examples

* Tue Apr 05 2022 Cleber Rosa <crosa@redhat.com> - 96.0-1
- New release

* Mon Feb 14 2022 Jan Richter <jarichte@redhat.com> - 95.0-2
- Rename requirements to dependencies

* Wed Feb 09 2022 Cleber Rosa <crosa@redhat.com> - 95.0-1
- New release

* Fri Jan 21 2022 Beraldo Leal <bleal@redhat.com> - 94.0-2
- Added new binary for 'avocado-external-runner'

* Mon Dec 20 2021 Avocado Developer <avocado@redhat.com> - 94.0-1
- New release

* Mon Dec 13 2021 Cleber Rosa <crosa@redhat.com> - 93.0-3
- Removed executable mode from avocado/core/nrunner.py

* Wed Nov 17 2021 Ana Guerrero Lopez <anguerre@redhat.com> - 93.0-2
- Adjust selftest/check.py to use new --skip option

* Wed Nov 17 2021 Cleber Rosa <crosa@redhat.com> - 93.0-1
- New release

* Fri Nov 12 2021 Cleber Rosa <crosa@redhat.com> - 92.0-4
- Do not require genisoimage on EL9

* Thu Nov 11 2021 Cleber Rosa <cleber@redhat.com> - 92.0-3
- Skip resultsdb plugin build on Fedora 36 due to broken resultsdb-api
  release

* Wed Oct 20 2021 Ana Guerrero Lopez <anguerre@redhat.com> - 92.0-2
- Replace the %global with_tests macro with %bcond_without to allow
  disable the tests directly in the command line.

* Tue Oct 19 2021 Cleber Rosa <cleber@redhat.com> - 92.0-1
- New release

* Fri Sep 17 2021 Beraldo Leal <bleal@redhat.com> - 91.0-3
- Removed avocado-runner-exec since we have avocado-runner-exec-test.

* Thu Sep 16 2021 Ana Guerrero Lopez <anguerre@redhat.com> - 91.0-2
- Minor update to the selftest/check.py call

* Mon Aug 30 2021 Cleber Rosa <crosa@redhat.com> - 91.0-1
- New release

* Thu Aug 05 2021 Ana Guerrero Lopez <anguerre@redhat.com> - 90.0-2
- Use new options of check.py to run tests.

* Mon Jul 26 2021 Cleber Rosa <crosa@redhat.com> - 90.0-1
- New release

* Mon Jun 28 2021 Merlin Mathesius <mmathesi@redhat.com> - 89.0-2
- Spec file cleanup identified during downstream package review.

* Mon Jun 21 2021 Cleber Rosa <cleber@redhat.com> - 89.0-1
- New release

* Sun May 23 2021 Cleber Rosa <cleber@redhat.com> - 88.1-2
- Remove /usr/bin/python[23] requirement exclusion

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
