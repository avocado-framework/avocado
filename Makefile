PYTHON=$(shell which python)
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
	@echo "make source - Create source package"
	@echo "make install - Install on local system"
	@echo "make build-deb-src - Generate a source debian package"
	@echo "make build-deb-bin - Generate a binary debian package"
	@echo "make build-deb-all - Generate both source and binary debian packages"
	@echo "make srpm - Generate a source RPM package (.srpm)"
	@echo "make rpm  - Generate binary RPMs"
	@echo "make man - Generate the avocado man page"
	@echo "make check - Runs tree static check, unittests and functional tests"
	@echo "make clean - Get rid of scratch and byte files"
	@echo "Release related targets:"
	@echo "make source-release - Create source package for the latest tagged release"
	@echo "make srpm-release - Generate a source RPM package (.srpm) for the latest tagged release"
	@echo "make rpm-release  - Generate binary RPMs for the latest tagged release"

source: clean
	if test ! -d SOURCES; then mkdir SOURCES; fi
	git archive --prefix="avocado-$(COMMIT)/" -o "SOURCES/avocado-$(VERSION)-$(SHORT_COMMIT).tar.gz" HEAD

source-release: clean
	if test ! -d SOURCES; then mkdir SOURCES; fi
	git archive --prefix="avocado-$(RELEASE_COMMIT)/" -o "SOURCES/avocado-$(VERSION)-$(RELEASE_SHORT_COMMIT).tar.gz" $(VERSION)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

prepare-source:
	# build the source package in the parent directory
	# then rename it to project_version.orig.tar.gz
	dch -D "vivid" -M -v "$(VERSION)" "Automated (make builddeb) build."
	$(PYTHON) setup.py sdist $(COMPILE) --dist-dir=../
	rename -f 's/$(PROJECT)-(.*)\.tar\.gz/$(PROJECT)_$$1\.orig\.tar\.gz/' ../*

build-deb-src: prepare-source
	# build the source package
	dpkg-buildpackage -S -elookkas@gmail.com -rfakeroot

build-deb-bin: prepare-source
	# build binary package
	dpkg-buildpackage -b -rfakeroot

build-deb-all: prepare-source
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
	find . -name '*.pyc' -delete
	rm -f man/avocado.1
	rm -f man/avocado-rest-client.1
	rm -rf docs/build
	find docs/source/api/ -name '*.rst' -delete
	for MAKEFILE in $(AVOCADO_PLUGINS);\
		do AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE unlink &>/dev/null && echo ">> UNLINK $$MAKEFILE" || echo ">> SKIP $$MAKEFILE";\
	done

install-requirements-all: install-requirements install-requirements-selftests

install-requirements:
	grep -v '^#' requirements.txt | xargs -n 1 pip install

install-requirements-selftests:
	grep -v '^#' requirements-selftests.txt | xargs -n 1 pip install

check: clean check_cyclical modules_boundaries
	rm -rf /var/tmp/avocado*
	rm -rf /tmp/avocado*
	selftests/checkall
	selftests/check_tmp_dirs

check_cyclical:
	selftests/cyclical_deps avocado

modules_boundaries:
	selftests/modules_boundaries

link:
	for MAKEFILE in $(AVOCADO_PLUGINS);\
		do AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$MAKEFILE link &>/dev/null && echo ">> LINK $$MAKEFILE" || echo ">> SKIP $$MAKEFILE";\
	done

man: man/avocado.1 man/avocado-rest-client.1

.PHONY: source install clean check link

# implicit rule/recipe for man page creation
%.1: %.rst
	rst2man $< $@
