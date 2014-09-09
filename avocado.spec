Summary: Avocado Test Framework
Name: avocado
Version: 0.12.0
Release: 1%{?dist}
License: GPLv2
Group: Development/Tools
URL: http://avocado-framework.readthedocs.org/
Source: avocado-%{version}.tar.gz
BuildRequires: python2-devel, python-docutils, python-yaml
BuildArch: noarch
Requires: python, python-requests, python-yaml, fabric

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
%config(noreplace)/etc/avocado/settings.ini
%{_bindir}/avocado
%{python_sitelib}/avocado*
%{_mandir}/man1/avocado.1.gz

%package tests
Summary: Avocado Test Framework Sample Tests
Requires: avocado

%description tests
The set of example tests that are part of the Avocado framework.

%files tests
%{_datadir}/avocado/tests

%changelog
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
