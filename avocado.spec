Summary: Avocado Test Framework
Name: avocado
Version: 0.8.0
Release: 2%{?dist}
License: GPLv2
Group: Development/Tools
URL: http://avocado-framework.readthedocs.org/
Source: avocado-%{version}.tar.gz
BuildRequires: python2-devel
BuildArch: noarch
Requires: python, python-requests

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%prep
%setup -q

%build
%{__python} setup.py build

%install
%{__python} setup.py install --root %{buildroot} --skip-build

%files
%defattr(-,root,root,-)
%doc README.rst LICENSE
%dir /etc/avocado
%config(noreplace)/etc/avocado/settings.ini
%{_bindir}/avocado
%{python_sitelib}/avocado*

%package tests
Summary: Avocado Test Framework Sample Tests
Requires: avocado

%description tests
The set of example tests that are part of the Avocado framework.

%files tests
%{_datadir}/avocado/tests

%changelog
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
