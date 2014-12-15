Summary: Avocado Test Framework
Name: avocado
Version: 0.17.0
Release: 1%{?dist}
License: GPLv2
Group: Development/Tools
URL: https://github.com/avocado-framework/avocado
Source: avocado-%{version}.tar.gz
BuildRequires: python2-devel, python-docutils, python-yaml
BuildArch: noarch
Requires: python, python-requests, python-yaml, fabric, pyliblzma

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%prep
%setup -q

%build
%{__python} setup.py build
%{__python2} /usr/bin/rst2man man/avocado.rst man/avocado.1

%install
%{__python} setup.py install --root %{buildroot} --skip-build
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1

%files
%defattr(-,root,root,-)
%doc README.rst LICENSE
%dir /etc/avocado
%dir /etc/avocado/conf.d
%config(noreplace)/etc/avocado/avocado.conf
%config(noreplace)/etc/avocado/conf.d/README
%{_bindir}/avocado
%exclude %{python_sitelib}/avocado/plugins/htmlresult.py*
%exclude %{python_sitelib}/avocado/plugins/resources/htmlresult/*
%{python_sitelib}/avocado*
%{_mandir}/man1/avocado.1.gz

%package plugins-output-html
Summary: Avocado HTML report plugin
Requires: avocado, pystache

%description plugins-output-html
Adds to avocado the ability to generate an HTML report at every job results
directory. It also gives the user the ability to write a report on an
arbitrary filesystem location.

%files plugins-output-html
%{python_sitelib}/avocado/plugins/htmlresult.py*
%{python_sitelib}/avocado/plugins/resources/htmlresult/*

%package examples
Summary: Avocado Test Framework Example Tests
Requires: avocado

%description examples
The set of example tests present in the upstream tree of the Avocado framework.
Some of them are used as functional tests of the framework, others serve as
examples of how to write tests on your own.

%files examples
%{_datadir}/avocado/tests
%{_datadir}/avocado/wrappers

%changelog
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
