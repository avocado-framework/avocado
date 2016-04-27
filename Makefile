#
# NOTE: to build Avocado RPM packages extra deps not present out of the box
# are necessary. These packages are currently hosted at:
#
# https://repos-avocadoproject.rhcloud.com/static/avocado-fedora.repo
# or
# https://repos-avocadoproject.rhcloud.com/static/avocado-el.repo
#
# Since the RPM build steps are based on mock, edit your chroot config
# file (/etc/mock/<your-config>.cnf) and add the COPR repo configuration there.
#

PYTHON=$(shell which python)
PYTHON26=$(shell $(PYTHON) -V 2>&1 | grep 2.6 -q && echo true || echo false)
VERSION=$(shell $(PYTHON) $(CURDIR)/avocado/core/version.py)
DESTDIR=/
BUILDIR=$(CURDIR)/debian/avocado
PROJECT=avocado
AVOCADO_DIRNAME=$(shell echo $${PWD\#\#*/})
AVOCADO_PLUGINS=$(filter-out ../$(AVOCADO_DIRNAME), $(wildcard ../*))
RELEASE_COMMIT=$(shell git log --pretty=format:'%H' -n 1 $(VERSION))
RELEASE_SHORT_COMMIT=$(shell git log --pretty=format:'%h' -n 1 $(VERSION))

COMMIT=$(shell git log --pretty=format:'%H' -n 1)
SHORT_COMMIT=$(shell git log --pretty=format:'%h' -n 1)

all:
	@echo
	@echo "Development related targets:"
	@echo "check:      Runs tree static check, unittests and functional tests"
	@echo "develop:    Runs 'python setup.py --develop on this tree alone"
	@echo "link:       Runs 'python setup.py --develop' in all subprojects and links the needed resources"
	@echo "clean:      Get rid of scratch, byte files and removes the links to other subprojects"
	@echo "selfcheck:  Runs tree static check, unittests and functional tests using Avocado itself"
	@echo
	@echo "Package requirements related targets"
	@echo "requirements:            Install runtime requirements"
	@echo "requirements-selftests:  Install runtime and selftests requirements"
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
	@echo "Debian related targets:"
	@echo "deb:      Generate both source and binary debian packages"
	@echo "deb-src:  Generate a source debian package"
	@echo "deb-bin:  Generate a binary debian package"
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

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

deb-prepare-source:
	# build the source package in the parent directory
	# then rename it to project_version.orig.tar.gz
	dch -D "vivid" -M -v "$(VERSION)" "Automated (make builddeb) build."
	$(PYTHON) setup.py sdist $(COMPILE) --dist-dir=../
	rename -f 's/$(PROJECT)-(.*)\.tar\.gz/$(PROJECT)_$$1\.orig\.tar\.gz/' ../*

deb-src: deb-prepare-source
	# build the source package
	dpkg-buildpackage -S -elookkas@gmail.com -rfakeroot

deb-bin: deb-prepare-source
	# build binary package
	dpkg-buildpackage -b -rfakeroot

deb: deb-prepare-source
	# build both source and binary packages
	dpkg-buildpackage -i -I -rfakeroot

srpm: source
	if test ! -d BUILD/SRPM; then mkdir -p BUILD/SRPM; fi
	mock --resultdir BUILD/SRPM -D "commit $(COMMIT)" --buildsrpm --spec avocado.spec --sources SOURCES

rpm: srpm
	if test ! -d BUILD/RPM; then mkdir -p BUILD/RPM; fi
	mock --resultdir BUILD/RPM -D "commit $(COMMIT)" --rebuild BUILD/SRPM/avocado-$(VERSION)-*.src.rpm

srpm-release: source-release
	if test ! -d BUILD/SRPM; then mkdir -p BUILD/SRPM; fi
	mock --resultdir BUILD/SRPM -D "commit $(RELEASE_COMMIT)" --buildsrpm --spec avocado.spec --sources SOURCES

rpm-release: srpm-release
	if test ! -d BUILD/RPM; then mkdir -p BUILD/RPM; fi
	mock --resultdir BUILD/RPM -D "commit $(RELEASE_COMMIT)" --rebuild BUILD/SRPM/avocado-$(VERSION)-*.src.rpm

clean:
	$(PYTHON) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean || true
	rm -rf build/ MANIFEST BUILD BUILDROOT SPECS RPMS SRPMS SOURCES
	rm -f man/avocado.1
	rm -f man/avocado-rest-client.1
	rm -rf docs/build
	find docs/source/api/ -name '*.rst' -delete
	for MAKEFILE in $(AVOCADO_PLUGINS);\
		do AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE unlink &>/dev/null && echo ">> UNLINK $$MAKEFILE" || echo ">> SKIP $$MAKEFILE";\
	done
	$(PYTHON) setup.py develop --uninstall $(shell $(PYTHON26) || echo --user)
	rm -rf avocado.egg-info
	rm -rf /var/tmp/avocado*
	rm -rf /tmp/avocado*
	find . -name '*.pyc' -delete

requirements:
	- pip install "pip>=6.0.1"
	- pip install -r requirements.txt

requirements-selftests: requirements
	- pip install -r requirements-selftests.txt

smokecheck:
	./scripts/avocado run passtest

check: clean develop check_cyclical modules_boundaries
	selftests/checkall
	selftests/check_tmp_dirs

selfcheck: clean check_cyclical modules_boundaries
	AVOCADO_SELF_CHECK=1 selftests/checkall
	selftests/check_tmp_dirs

check_cyclical:
	selftests/cyclical_deps avocado

modules_boundaries:
	selftests/modules_boundaries

develop:
	$(PYTHON) setup.py develop $(shell $(PYTHON26) || echo --user)

link: develop
	for MAKEFILE in $(AVOCADO_PLUGINS);\
		do AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE link &>/dev/null && echo ">> LINK $$MAKEFILE" || echo ">> SKIP $$MAKEFILE";\
	done

man: man/avocado.1 man/avocado-rest-client.1

.PHONY: source install clean check link

# implicit rule/recipe for man page creation
%.1: %.rst
	rst2man $< $@
