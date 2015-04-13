PYTHON=`which python`
DESTDIR=/
BUILDIR=$(CURDIR)/debian/avocado
PROJECT=avocado
VERSION=`$(CURDIR)/avocado/version.py`

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
	$(PYTHON) setup.py sdist $(COMPILE) --dist-dir=SOURCES --prune

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
	rm -f docs/build/api/*.rst
	test -L avocado/virt && rm -f avocado/virt || true
	test -L avocado/plugins/virt.py && rm -f avocado/plugins/virt.py || true
	test -L avocado/plugins/virt_bootstrap.py && rm -f avocado/plugins/virt_bootstrap.py || true

check:
	selftests/checkall

link:
	test -d ../avocado-virt/avocado/virt && ln -s ../../avocado-virt/avocado/virt avocado || true
	test -f ../avocado-virt/avocado/plugins/virt.py && ln -s ../../../avocado-virt/avocado/plugins/virt.py avocado/plugins/ || true
	test -f ../avocado-virt/avocado/plugins/virt_bootstrap.py && ln -s ../../../avocado-virt/avocado/plugins/virt_bootstrap.py avocado/plugins/ || true

man: man/avocado.1 man/avocado-rest-client.1

.PHONY: source install clean check link

# implicit rule/recipe for man page creation
%.1: %.rst
	rst2man $< $@
