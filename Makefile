PYTHON=`which python`
DESTDIR=/
BUILDIR=$(CURDIR)/debian/avocado
PROJECT=avocado
VERSION=`$(CURDIR)/avocado/core/version.py`

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
	$(PYTHON) setup.py sdist $(COMPILE) --dist-dir=../ --prune
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
	rm -f docs/source/api/*.rst
	test -L avocado/virt && rm -f avocado/virt || true
	test -L avocado/core/plugins/virt.py && rm -f avocado/core/plugins/virt.py || true
	test -L avocado/core/plugins/virt_bootstrap.py && rm -f avocado/core/plugins/virt_bootstrap.py || true
	test -L avocado/core/plugins/virt_test.py && rm -f avocado/core/plugins/virt_test.py || true
	test -L avocado/core/plugins/virt_test_list.py && rm -f avocado/core/plugins/virt_test_list.py || true
	test -L etc/avocado/conf.d/virt-test.conf && rm -f etc/avocado/conf.d/virt-test.conf || true

check: clean
	selftests/checkall

check_cyclical:
	selftests/cyclical_deps avocado

link:
	test -d ../avocado-virt/avocado/virt && ln -s ../../avocado-virt/avocado/virt avocado || true
	test -f ../avocado-virt/avocado/core/plugins/virt.py && ln -s ../../../../avocado-virt/avocado/core/plugins/virt.py avocado/core/plugins/ || true
	test -f ../avocado-virt/avocado/core/plugins/virt_bootstrap.py && ln -s ../../../../avocado-virt/avocado/core/plugins/virt_bootstrap.py avocado/core/plugins/ || true
	test -f ../avocado-vt/etc/avocado/conf.d/virt-test.conf && ln -s ../../../../avocado-vt/etc/avocado/conf.d/virt-test.conf etc/avocado/conf.d/ || true
	test -f ../avocado-vt/avocado/core/plugins/virt_test.py && ln -s ../../../../avocado-vt/avocado/core/plugins/virt_test.py avocado/core/plugins/ || true
	test -f ../avocado-vt/avocado/core/plugins/virt_test_list.py && ln -s ../../../../avocado-vt/avocado/core/plugins/virt_test_list.py avocado/core/plugins/ || true

man: man/avocado.1 man/avocado-rest-client.1

.PHONY: source install clean check link

# implicit rule/recipe for man page creation
%.1: %.rst
	rst2man $< $@
