#
# NOTE: to build Avocado RPM packages extra deps not present out of the box
# are necessary. These packages are currently hosted at:
#
# https://repos-avocadoproject.rhcloud.com/static/avocado-fedora.repo
# or
# https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo
#
# Since the RPM build steps are based on mock, edit your chroot config
# file (/etc/mock/<your-config>.cnf) and add the corresponding repo
# configuration there.
#

PYTHON=$(shell which python)
PYTHON_DEVELOP_ARGS=$(shell if ($(PYTHON) setup.py develop --help 2>/dev/null | grep -q '\-\-user'); then echo "--user"; else echo ""; fi)
VERSION=$(shell $(PYTHON) setup.py --version 2>/dev/null)
DESTDIR=/
AVOCADO_DIRNAME=$(shell echo $${PWD\#\#*/})
AVOCADO_EXTERNAL_PLUGINS=$(filter-out ../$(AVOCADO_DIRNAME), $(shell find ../ -maxdepth 1 -mindepth 1 -type d))
AVOCADO_OPTIONAL_PLUGINS=$(shell find ./optional_plugins -maxdepth 1 -mindepth 1 -type d)
AVOCADO_PLUGINS=$(AVOCADO_EXTERNAL_PLUGINS)
AVOCADO_PLUGINS+=$(AVOCADO_OPTIONAL_PLUGINS)
RELEASE_COMMIT=$(shell git log --pretty=format:'%H' -n 1 $(VERSION))
RELEASE_SHORT_COMMIT=$(shell git log --pretty=format:'%h' -n 1 $(VERSION))
COMMIT=$(shell git log --pretty=format:'%H' -n 1)
SHORT_COMMIT=$(shell git log --pretty=format:'%h' -n 1)
MOCK_CONFIG=default

all:
	@echo
	@echo "Development related targets:"
	@echo "check:      Runs tree static check, unittests and functional tests"
	@echo "check-long: Runs tree static check, unittests and long functional tests"
	@echo "develop:    Runs 'python setup.py --develop on this tree alone"
	@echo "link:       Runs 'python setup.py --develop' in all subprojects and links the needed resources"
	@echo "clean:      Get rid of scratch, byte files and removes the links to other subprojects"
	@echo "selfcheck:  Runs tree static check, unittests and functional tests using Avocado itself"
	@echo "spell:      Runs spell checker on comments and docstrings (requires python-enchant)"
	@echo
	@echo "Package requirements related targets"
	@echo "requirements:            Install runtime requirements"
	@echo "requirements-selftests:  Install runtime and selftests requirements"
	@echo "requirements-plugins:    Install plugins requirements"
	@echo
	@echo "Platform independent distribution/installtion related targets:"
	@echo "source:   Create source package"
	@echo "install:  Install on local system"
	@echo "man:      Generate the avocado man page"
	@echo
	@echo "RPM related targets:"
	@echo "srpm:  Generate a source RPM package (.srpm)"
	@echo "rpm:   Generate binary RPMs"
	@echo
	@echo "Release related targets:"
	@echo "source-release:  Create source package for the latest tagged release"
	@echo "srpm-release:    Generate a source RPM package (.srpm) for the latest tagged release"
	@echo "rpm-release:     Generate binary RPMs for the latest tagged release"
	@echo

source: clean
	if test ! -d SOURCES; then mkdir SOURCES; fi
	git archive --prefix="avocado-$(COMMIT)/" -o "SOURCES/avocado-$(VERSION)-$(SHORT_COMMIT).tar.gz" HEAD

source-release: clean
	if test ! -d SOURCES; then mkdir SOURCES; fi
	git archive --prefix="avocado-$(RELEASE_COMMIT)/" -o "SOURCES/avocado-$(VERSION)-$(RELEASE_SHORT_COMMIT).tar.gz" $(VERSION)

source-pypi: clean
	if test ! -d PYPI_UPLOAD; then mkdir PYPI_UPLOAD; fi
	git archive --prefix="avocado-framework/" -o "PYPI_UPLOAD/avocado-framework-$(VERSION).tar.gz" $(VERSION)

pypi: source-pypi develop
	cp avocado_framework.egg-info/PKG-INFO PYPI_UPLOAD/PKG-INFO
	@echo
	@echo "Please use the files on PYPI_UPLOAD dir to upload a new version to PyPI"
	@echo "The URL to do that may be a bit tricky to find, so here it is:"
	@echo " https://pypi.python.org/pypi?%3Aaction=submit_form"
	@echo

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

srpm: source
	if test ! -d BUILD/SRPM; then mkdir -p BUILD/SRPM; fi
	mock -r $(MOCK_CONFIG) --resultdir BUILD/SRPM -D "commit $(COMMIT)" --buildsrpm --spec avocado.spec --sources SOURCES

rpm: srpm
	if test ! -d BUILD/RPM; then mkdir -p BUILD/RPM; fi
	mock -r $(MOCK_CONFIG) --resultdir BUILD/RPM -D "commit $(COMMIT)" --rebuild BUILD/SRPM/avocado-$(VERSION)-*.src.rpm

srpm-release: source-release
	if test ! -d BUILD/SRPM; then mkdir -p BUILD/SRPM; fi
	mock -r $(MOCK_CONFIG) --resultdir BUILD/SRPM -D "commit $(RELEASE_COMMIT)" --buildsrpm --spec avocado.spec --sources SOURCES

rpm-release: srpm-release
	if test ! -d BUILD/RPM; then mkdir -p BUILD/RPM; fi
	mock -r $(MOCK_CONFIG) --resultdir BUILD/RPM -D "commit $(RELEASE_COMMIT)" --rebuild BUILD/SRPM/avocado-$(VERSION)-*.src.rpm

clean:
	$(PYTHON) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean || true
	rm -rf build/ MANIFEST BUILD BUILDROOT SPECS RPMS SRPMS SOURCES PYPI_UPLOAD
	rm -f man/avocado.1
	rm -f man/avocado-rest-client.1
	rm -rf docs/build
	find docs/source/api/ -name '*.rst' -delete
	for MAKEFILE in $(AVOCADO_PLUGINS); do\
		if test -f $$MAKEFILE/Makefile -o -f $$MAKEFILE/setup.py; then echo ">> UNLINK $$MAKEFILE";\
			if test -f $$MAKEFILE/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE unlink &>/dev/null;\
			elif test -f $$MAKEFILE/setup.py; then cd $$MAKEFILE; $(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$MAKEFILE"; fi;\
	done
	$(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS)
	rm -rf avocado_framework.egg-info
	rm -rf /var/tmp/avocado*
	rm -rf /tmp/avocado*
	find . -name '*.pyc' -delete

pip:
	$(PYTHON) -m pip --version || $(PYTHON) -c "import os; import sys; import urllib; f = urllib.urlretrieve('https://bootstrap.pypa.io/get-pip.py')[0]; os.system('%s %s' % (sys.executable, f))"

requirements: pip
	- pip install "pip>=6.0.1"
	- pip install -r requirements.txt

requirements-selftests: requirements
	- pip install -r requirements-selftests.txt

requirements-plugins: requirements
	for MAKEFILE in $(AVOCADO_PLUGINS);\
		do AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE requirements &>/dev/null && echo ">> DONE $$MAKEFILE" || echo ">> SKIP $$MAKEFILE";\
	done

smokecheck: clean develop
	./scripts/avocado run passtest.py

check: clean develop check_cyclical modules_boundaries
	selftests/checkall
	selftests/check_tmp_dirs

check-long: clean develop check_cyclical modules_boundaries
	AVOCADO_CHECK_LONG=1 selftests/checkall
	selftests/check_tmp_dirs

selfcheck: clean check_cyclical modules_boundaries develop
	AVOCADO_SELF_CHECK=1 selftests/checkall
	selftests/check_tmp_dirs

check_cyclical:
	selftests/cyclical_deps avocado

modules_boundaries:
	selftests/modules_boundaries

develop:
	$(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS)
	for MAKEFILE in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$MAKEFILE/Makefile -o -f $$MAKEFILE/setup.py; then echo ">> LINK $$MAKEFILE";\
			if test -f $$MAKEFILE/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE link &>/dev/null;\
			elif test -f $$MAKEFILE/setup.py; then cd $$MAKEFILE; $(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$MAKEFILE"; fi;\
	done

link: develop
	for MAKEFILE in $(AVOCADO_EXTERNAL_PLUGINS); do\
		if test -f $$MAKEFILE/Makefile -o -f $$MAKEFILE/setup.py; then echo ">> LINK $$MAKEFILE";\
			if test -f $$MAKEFILE/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE link &>/dev/null;\
			elif test -f $$MAKEFILE/setup.py; then cd $$MAKEFILE; $(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$MAKEFILE"; fi;\
	done

spell:
	pylint --errors-only --disable=all --enable=spelling --spelling-dict=en_US --spelling-private-dict-file=spell.ignore * && echo OK

man: man/avocado.1 man/avocado-rest-client.1

variables:
	@echo "PYTHON: $(PYTHON)"
	@echo "VERSION: $(VERSION)"
	@echo "DESTDIR: $(DESTDIR)"
	@echo "AVOCADO_DIRNAME: $(AVOCADO_DIRNAME)"
	@echo "AVOCADO_PLUGINS: $(AVOCADO_PLUGINS)"
	@echo "RELEASE_COMMIT: $(RELEASE_COMMIT)"
	@echo "RELEASE_SHORT_COMMIT: $(RELEASE_SHORT_COMMIT)"
	@echo "COMMIT: $(COMMIT)"
	@echo "SHORT_COMMIT: $(SHORT_COMMIT)"
	@echo "MOCK_CONFIG: $(MOCK_CONFIG)"
	@echo "PYTHON_DEVELOP_ARGS: $(PYTHON_DEVELOP_ARGS)"

.PHONY: source install clean check link variables

# implicit rule/recipe for man page creation
%.1: %.rst
	rst2man $< $@
