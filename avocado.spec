%global modulename avocado
%if ! 0%{?commit:1}
 %define commit bde85d53a2e1ffde02b2f65ef1f29f912acf5d32
%endif
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Summary: Avocado Test Framework
Name: avocado
Version: 0.30.0
Release: 1%{?dist}
License: GPLv2
Group: Development/Tools
URL: http://avocado-framework.github.io/
Source0: https://github.com/avocado-framework/%{name}/archive/%{commit}/%{name}-%{version}-%{shortcommit}.tar.gz
BuildArch: noarch
Requires: python, python-requests, fabric, pyliblzma, libvirt-python, pystache, gdb, gdb-gdbserver, python-stevedore
BuildRequires: python2-devel, python-setuptools, python-docutils, python-mock, python-psutil, python-sphinx, python-requests, aexpect, pystache, yum

%if 0%{?el6}
Requires: PyYAML
Requires: python-argparse, python-importlib, python-logutils, python-unittest2
BuildRequires: PyYAML
BuildRequires: python-argparse, python-importlib, python-logutils, python-unittest2
%else
Requires: python-yaml
BuildRequires: python-yaml, fabric
%endif

%if !0%{?el7}
BuildRequires: python-flexmock
%endif

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%prep
%setup -q -n %{name}-%{commit}

%build
%{__python} setup.py build
%{__make} man

%install
%{__python} setup.py install --root %{buildroot} --skip-build
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
%{__install} -m 0644 man/avocado-rest-client.1 %{buildroot}%{_mandir}/man1/avocado-rest-client.1

# Running the unittests is currently disabled on EL6 because fabric is
# missing on EPEL 6 and also on EL7 because python-flexmock is missing
# on EPEL7.
%if !0%{?rhel}
%check
selftests/run
%endif

%files
%defattr(-,root,root,-)
%doc README.rst LICENSE
%dir /etc/avocado
%dir /etc/avocado/conf.d
%dir /etc/avocado/sysinfo
%config(noreplace)/etc/avocado/avocado.conf
%config(noreplace)/etc/avocado/conf.d/README
%config(noreplace)/etc/avocado/conf.d/gdb.conf
%config(noreplace)/etc/avocado/sysinfo/commands
%config(noreplace)/etc/avocado/sysinfo/files
%config(noreplace)/etc/avocado/sysinfo/profilers
%{python_sitelib}/avocado*
%{_bindir}/avocado
%{_bindir}/avocado-rest-client
%{_mandir}/man1/avocado.1.gz
%{_mandir}/man1/avocado-rest-client.1.gz
%{_docdir}/avocado/avocado.rst
%{_docdir}/avocado/avocado-rest-client.rst
%exclude %{python_sitelib}/avocado/core/plugins/htmlresult.py*
%exclude %{python_sitelib}/avocado/core/plugins/resources/htmlresult/*
%{_libexecdir}/avocado/avocado-bash-utils
%{_libexecdir}/avocado/avocado_debug
%{_libexecdir}/avocado/avocado_error
%{_libexecdir}/avocado/avocado_info
%{_libexecdir}/avocado/avocado_warn

%package plugins-output-html
Summary: Avocado HTML report plugin
Requires: avocado, pystache

%description plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files plugins-output-html
%{python_sitelib}/avocado/core/plugins/htmlresult.py*
%{python_sitelib}/avocado/core/plugins/resources/htmlresult/*

%package examples
Summary: Avocado Test Framework Example Tests
Requires: avocado

%description examples
The set of example tests present in the upstream tree of the Avocado framework.
Some of them are used as functional tests of the framework, others serve as
examples of how to write tests on your own.

%files examples
%{_datadir}/avocado/tests
%{_datadir}/avocado/simpletests
%{_datadir}/avocado/wrappers

%changelog
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
