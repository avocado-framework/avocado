Summary: Avocado Test Framework
Name: avocado
Version: 0.21.0
Release: 4%{?dist}
License: GPLv2
Group: Development/Tools
URL: http://avocado-framework.github.io/
Source: avocado-%{version}.tar.gz
BuildArch: noarch

%if "%{?dist}" == ".el6"
Requires: python, python-requests, fabric, pyliblzma, libvirt-python, pystache, PyYAML, python-argparse, python-unittest2, python-logutils, python-importlib
BuildRequires: python2-devel, python-docutils, PyYAML, python-logutils
%else
Requires: python, python-requests, fabric, pyliblzma, libvirt-python, pystache, python-yaml
BuildRequires: python2-devel, python-docutils, python-yaml
%endif

%description
Avocado is a set of tools and libraries (what people call
these days a framework) to perform automated testing.

%prep
%setup -q

%build
%{__python} setup.py build
%if "%{?dist}" == ".el6"
%{__python} /usr/bin/rst2man man/avocado.rst man/avocado.1
%{__python} /usr/bin/rst2man man/avocado-rest-client.rst man/avocado-rest-client.1
%else
%{__python2} /usr/bin/rst2man man/avocado.rst man/avocado.1
%{__python2} /usr/bin/rst2man man/avocado-rest-client.rst man/avocado-rest-client.1
%endif

%install
%{__python} setup.py install --root %{buildroot} --skip-build
%{__mkdir} -p %{buildroot}%{_mandir}/man1
%{__install} -m 0644 man/avocado.1 %{buildroot}%{_mandir}/man1/avocado.1
%{__install} -m 0644 man/avocado-rest-client.1 %{buildroot}%{_mandir}/man1/avocado-rest-client.1

%files
%defattr(-,root,root,-)
%doc README.rst LICENSE
%dir /etc/avocado
%dir /etc/avocado/conf.d
%config(noreplace)/etc/avocado/avocado.conf
%config(noreplace)/etc/avocado/conf.d/README
%{python_sitelib}/avocado*
%{_bindir}/avocado
%{_bindir}/avocado-rest-client
%{_mandir}/man1/avocado.1.gz
%{_mandir}/man1/avocado-rest-client.1.gz
%{_docdir}/avocado/avocado.rst
%{_docdir}/avocado/avocado-rest-client.rst
%exclude %{python_sitelib}/avocado/plugins/htmlresult.py*
%exclude %{python_sitelib}/avocado/plugins/resources/htmlresult/*
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
%{_datadir}/avocado/api

%changelog
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
