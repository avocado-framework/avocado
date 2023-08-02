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
	@echo
	@echo "Platform independent distribution/installation related targets:"
	@echo "install:      Install on local system"
	@echo "uninstall:    Uninstall Avocado and also subprojects"
	@echo "man:          Generate the avocado man page"
	@echo "pip:          Auxiliary target to install pip. (It's not recommended to run this directly)"
	@echo

include Makefile.include

DESTDIR=/
AVOCADO_DIRNAME=$(shell basename ${PWD})
AVOCADO_OPTIONAL_PLUGINS=$(shell find ./optional_plugins -maxdepth 1 -mindepth 1 -type d)


clean:
	$(PYTHON) setup.py clean --all

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

uninstall:
	$(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS)

requirements-dev: pip
	- $(PYTHON) -m pip install -r requirements-dev.txt $(PYTHON_DEVELOP_ARGS)

smokecheck: clean uninstall develop
	$(PYTHON) -m avocado run examples/tests/passtest.py

check: clean uninstall develop
	# Unless manually set, this is equivalent to AVOCADO_CHECK_LEVEL=0
	$(PYTHON) selftests/check.py

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

.PHONY: pip install clean uninstall requirements-dev smokecheck check develop develop-external variables man
