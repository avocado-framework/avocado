PYTHON=`which python`
DESTDIR=/
BUILDIR=$(CURDIR)/debian/avocado
PROJECT=avocado
VERSION=`$(CURDIR)/avocado/core/version.py`
AVOCADO_DIRNAME=$(shell echo $${PWD\#\#*/})
AVOCADO_PLUGINS=$(filter-out ../$(AVOCADO_DIRNAME), $(wildcard ../*))

all:
	@echo "make source - Create source package"
	@echo "make install - Install on local system"
	@echo "make build-deb-src - Generate a source debian package"
	@echo "make build-deb-bin - Generate a binary debian package"
	@echo "make build-deb-all - Generate both source and binary debian packages"
	@echo "make build-rpm-src - Generate a source RPM package (.srpm)"
	@echo "make build-rpm-all - Generate both source and binary RPMs"
	@echo "make man - Generate the avocado man page"
	@echo "make check - Runs tree static check, unittests and functional tests"
	@echo "make clean - Get rid of scratch and byte files"

source:
	if test ! -d SOURCES; then mkdir SOURCES; fi
	git archive --prefix="avocado-$(VERSION)/" -o "SOURCES/avocado-$(VERSION).tar.gz" HEAD

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

prepare-source:
	# build the source package in the parent directory
	# then rename it to project_version.orig.tar.gz
	dch -D "utopic" -M -v "$(VERSION)" "Automated (make builddeb) build."
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

build-rpm-src: source
	rpmbuild --define '_topdir %{getenv:PWD}' \
		 -bs avocado.spec

build-rpm-all: source
	rpmbuild --define '_topdir %{getenv:PWD}' \
		 -ba avocado.spec

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
