ifndef PYTHON
PYTHON=$(shell which python3 2>/dev/null || which python 2>/dev/null)
endif
VERSION=$(shell $(PYTHON) setup.py --version 2>/dev/null)
PYTHON_DEVELOP_ARGS=$(shell if ($(PYTHON) setup.py develop --help 2>/dev/null | grep -q '\-\-user'); then echo "--user"; else echo ""; fi)
DESTDIR=/
AVOCADO_DIRNAME=$(shell basename ${PWD})
AVOCADO_OPTIONAL_PLUGINS=$(shell find ./optional_plugins -maxdepth 1 -mindepth 1 -type d)
RELEASE_COMMIT=$(shell git log --pretty=format:'%H' -n 1 $(VERSION))
RELEASE_SHORT_COMMIT=$(shell git rev-parse --short=9 $(VERSION))
COMMIT=$(shell git log --pretty=format:'%H' -n 1)
COMMIT_DATE=$(shell git log --pretty='format:%cd' --date='format:%Y%m%d' -n 1)
SHORT_COMMIT=$(shell git rev-parse --short=9 HEAD)
MOCK_CONFIG=default
ARCHIVE_BASE_NAME=avocado
PYTHON_MODULE_NAME=avocado-framework
RPM_BASE_NAME=python-avocado


all:
	@echo
	@echo "Development related targets:"
	@echo "check:             Runs tree static check, unittests and fast functional tests"
	@echo "smokecheck:        Runs the simplest possible avocado test execution"
	@echo "develop:           Runs 'python setup.py --develop' on this tree alone"
	@echo "develop-external:  Install Avocado's external plugins in develop mode."
	@echo "                   You need to set AVOCADO_EXTERNAL_PLUGINS_PATH"
	@echo "clean:             Get rid of build scratch from this project and subprojects"
	@echo "variables:         Show the value of variables as defined in this Makefile or"
	@echo "                   given as input to make"
	@echo
	@echo "Package requirements related targets"
	@echo "requirements-dev:      Install development requirements"
	@echo "requirements-plugins:  Install plugins requirements"
	@echo
	@echo "Platform independent distribution/installation related targets:"
	@echo "source:       Create single source package with commit info, suitable for RPMs"
	@echo "source-pypi:  Create source packages suitable for PyPI"
	@echo "wheel:        Create binary wheel packages suitable for PyPI"
	@echo "pypi:         Create both source and binary wheel packages and show how to"
	@echo "              upload them to PyPI"
	@echo "python_build: Installs the build package, needed for source-pypi and wheel"
	@echo "install:      Install on local system"
	@echo "uninstall:    Uninstall Avocado and also subprojects"
	@echo "man:          Generate the avocado man page"
	@echo
	@echo "RPM related targets:"
	@echo "srpm:  Generate a source RPM package (.srpm)"
	@echo "rpm:   Generate binary RPMs"
	@echo
	@echo "Release related targets:"
	@echo "source-release:  Create source package for the latest tagged release"
	@echo "srpm-release:    Generate a source RPM package (.srpm) for the latest tagged release"
	@echo "rpm-release:        Generate binary RPMs for the latest tagged release"
	@echo "propagate-version:  Propagate './VERSION' to all plugins/modules"
	@echo

include Makefile.include

source-pypi: python_build
	if test ! -d PYPI_UPLOAD; then mkdir PYPI_UPLOAD; fi
	$(PYTHON) -m build --sdist -o PYPI_UPLOAD
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$PLUGIN/setup.py; then\
			echo ">> Creating source distribution for $$PLUGIN";\
			cd $$PLUGIN;\
			$(PYTHON) -m build --sdist -o ../../PYPI_UPLOAD;\
			cd -;\
                fi;\
	done

wheel: python_build
	if test ! -d PYPI_UPLOAD; then mkdir PYPI_UPLOAD; fi
	$(PYTHON) -m build -o PYPI_UPLOAD
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$PLUGIN/setup.py; then\
			echo ">> Creating wheel distribution for $$PLUGIN";\
			cd $$PLUGIN;\
			$(PYTHON) -m build -o ../../PYPI_UPLOAD;\
			cd -;\
                fi;\
	done

pypi: wheel
	@echo
	@echo "Please upload your packages running a command like: "
	@echo " twine upload -u <PYPI_USERNAME> PYPI_UPLOAD/*.{tar.gz,whl}"
	@echo

python_build: pip
	$(PYTHON) -m pip install $(PYTHON_DEVELOP_ARGS) build

clean:
	$(PYTHON) setup.py clean --all

uninstall:
	$(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS)

requirements-plugins:
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS);do\
		if test -f $$PLUGIN/Makefile; then echo ">> REQUIREMENTS (Makefile) $$PLUGIN"; AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN requirements &>/dev/null;\
		elif test -f $$PLUGIN/requirements.txt; then echo ">> REQUIREMENTS (requirements.txt) $$PLUGIN"; pip install $(PYTHON_DEVELOP_ARGS) -r $$PLUGIN/requirements.txt;\
		else echo ">> SKIP $$PLUGIN";\
		fi;\
	done;

requirements-dev: pip
	- $(PYTHON) -m pip install -r requirements-dev.txt

smokecheck: clean uninstall develop
	PYTHON=$(PYTHON) $(PYTHON) -m avocado run passtest.py

check: clean uninstall develop
	# Unless manually set, this is equivalent to AVOCADO_CHECK_LEVEL=0
	PYTHON=$(PYTHON) $(PYTHON) selftests/check.py
	selftests/check_tmp_dirs

develop:
	$(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS)

develop-external:
ifndef AVOCADO_EXTERNAL_PLUGINS_PATH
	$(error AVOCADO_EXTERNAL_PLUGINS_PATH is not defined)
endif
	$(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS) --external

man: man/avocado.1

%.1: %.rst
	$(PYTHON) setup.py man

variables:
	@echo "PYTHON: $(PYTHON)"
	@echo "VERSION: $(VERSION)"
	@echo "PYTHON_DEVELOP_ARGS: $(PYTHON_DEVELOP_ARGS)"
	@echo "DESTDIR: $(DESTDIR)"
	@echo "AVOCADO_DIRNAME: $(AVOCADO_DIRNAME)"
	@echo "AVOCADO_OPTIONAL_PLUGINS: $(AVOCADO_OPTIONAL_PLUGINS)"
	@echo "RELEASE_COMMIT: $(RELEASE_COMMIT)"
	@echo "RELEASE_SHORT_COMMIT: $(RELEASE_SHORT_COMMIT)"
	@echo "COMMIT: $(COMMIT)"
	@echo "COMMIT_DATE: $(COMMIT_DATE)"
	@echo "SHORT_COMMIT: $(SHORT_COMMIT)"
	@echo "MOCK_CONFIG: $(MOCK_CONFIG)"
	@echo "ARCHIVE_BASE_NAME: $(ARCHIVE_BASE_NAME)"
	@echo "PYTHON_MODULE_NAME: $(PYTHON_MODULE_NAME)"
	@echo "RPM_BASE_NAME: $(RPM_BASE_NAME)"

propagate-version:
	for DIR in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f "$$DIR/VERSION"; then\
			echo ">> Updating $$DIR"; echo "$(VERSION)" > "$$DIR/VERSION";\
		else echo ">> Skipping $$DIR"; fi;\
	done

.PHONY: source source-pypi wheel pypi install clean uninstall requirements-plugins requirements-dev smokecheck check develop develop-external propagate-version variables
