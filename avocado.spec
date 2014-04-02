Summary: Avocado Test Framework
Name: avocado
Version: 0.0.1
Release: 1%{?dist}
License: GPLv2
Group: Development/Tools
URL: https://github.com/lmr/avocado
Source: avocado-%{version}.tar.gz
BuildRequires: python2-devel
BuildArch: noarch
Requires: python

%description
Avocado is an experimental test framework that is built on the experience with
the autotest framework. It aims to implement the good concepts that make
autotest a good test suite, while trying to streamline and reduce some of its
shortcomings.

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
%{_datadir}/avocado

%changelog
* Wed Apr  2 2014 Ruda Moura <rmoura@redhat.com> - 0.0.1-1
- Created initial spec file
