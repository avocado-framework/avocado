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
	@echo "develop:           Runs 'python setup.py --develop' on this tree alone"
	@echo "develop-external:  Install Avocado's external plugins in develop mode. You need to set AVOCADO_EXTERNAL_PLUGINS_PATH"
	@echo "clean:             Get rid of build scratch from this project and subprojects"
	@echo
	@echo "Package requirements related targets"
	@echo "requirements-selftests:  Install runtime and selftests requirements"
	@echo "requirements-plugins:    Install plugins requirements"
	@echo
	@echo "Platform independent distribution/installation related targets:"
	@echo "source:    Create source package"
	@echo "install:   Install on local system"
	@echo "uninstall: Uninstall Avocado and also subprojects"
	@echo "man:      Generate the avocado man page"
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

source-pypi: clean
	if test ! -d PYPI_UPLOAD; then mkdir PYPI_UPLOAD; fi
	git archive --format="tar" --prefix="$(PYTHON_MODULE_NAME)/" $(VERSION) | tar --file - --delete '$(PYTHON_MODULE_NAME)/optional_plugins' > "PYPI_UPLOAD/$(PYTHON_MODULE_NAME)-$(VERSION).tar"
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$PLUGIN/setup.py; then\
			echo ">> Creating source distribution for $$PLUGIN";\
			cd $$PLUGIN;\
			$(PYTHON) setup.py sdist -d ../../PYPI_UPLOAD;\
			cd -;\
                fi;\
	done

wheel: clean
	if test ! -d PYPI_UPLOAD; then mkdir PYPI_UPLOAD; fi
	$(PYTHON) setup.py bdist_wheel -d PYPI_UPLOAD
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$PLUGIN/setup.py; then\
			echo ">> Creating wheel distribution for $$PLUGIN";\
			cd $$PLUGIN;\
			$(PYTHON) setup.py bdist_wheel -d ../../PYPI_UPLOAD;\
			cd -;\
                fi;\
	done

pypi: wheel source-pypi develop
	mkdir PYPI_UPLOAD/$(PYTHON_MODULE_NAME)
	cp avocado_framework.egg-info/PKG-INFO PYPI_UPLOAD/$(PYTHON_MODULE_NAME)
	tar rf "PYPI_UPLOAD/$(PYTHON_MODULE_NAME)-$(VERSION).tar" -C PYPI_UPLOAD $(PYTHON_MODULE_NAME)/PKG-INFO
	gzip -9 "PYPI_UPLOAD/$(PYTHON_MODULE_NAME)-$(VERSION).tar"
	rm -f PYPI_UPLOAD/$(PYTHON_MODULE_NAME)/PKG-INFO
	rmdir PYPI_UPLOAD/$(PYTHON_MODULE_NAME)
	@echo
	@echo "Please use the files on PYPI_UPLOAD dir to upload a new version to PyPI"
	@echo "The URL to do that may be a bit tricky to find, so here it is:"
	@echo " https://pypi.python.org/pypi?%3Aaction=submit_form"
	@echo
	@echo "Alternatively, you can also run a command like: "
	@echo " twine upload -u <PYPI_USERNAME> PYPI_UPLOAD/*.{tar.gz,whl}"
	@echo

clean:
	$(PYTHON) setup.py clean --all

uninstall:
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$PLUGIN/Makefile -o -f $$PLUGIN/setup.py; then echo ">> UNLINK $$PLUGIN";\
			if test -f $$PLUGIN/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN unlink &>/dev/null || echo ">> FAIL $$PLUGIN";\
			elif test -f $$PLUGIN/setup.py; then cd $$PLUGIN; $(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$PLUGIN"; fi;\
	done
	$(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS)

requirements-plugins:
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS);do\
		if test -f $$PLUGIN/Makefile; then echo ">> REQUIREMENTS (Makefile) $$PLUGIN"; AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN requirements &>/dev/null;\
		elif test -f $$PLUGIN/requirements.txt; then echo ">> REQUIREMENTS (requirements.txt) $$PLUGIN"; pip install $(PYTHON_DEVELOP_ARGS) -r $$PLUGIN/requirements.txt;\
		else echo ">> SKIP $$PLUGIN";\
		fi;\
	done;

requirements-selftests: pip
	- $(PYTHON) -m pip install -r requirements-selftests.txt

smokecheck: clean uninstall develop
	PYTHON=$(PYTHON) $(PYTHON) -m avocado run passtest.py

check: clean uninstall develop
	# Unless manually set, this is equivalent to AVOCADO_CHECK_LEVEL=0
	PYTHON=$(PYTHON) $(PYTHON) selftests/check.py
	selftests/check_tmp_dirs

develop:
	$(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS)
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$PLUGIN/Makefile -o -f $$PLUGIN/setup.py; then echo ">> LINK $$PLUGIN";\
			if test -f $$PLUGIN/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN PYTHON="$(PYTHON)" link &>/dev/null;\
			elif test -f $$PLUGIN/setup.py; then cd $$PLUGIN; $(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$PLUGIN"; fi;\
	done

develop-external:
ifndef AVOCADO_EXTERNAL_PLUGINS_PATH
	$(error AVOCADO_EXTERNAL_PLUGINS_PATH is not defined)
endif
	for PLUGIN in $(shell find $(AVOCADO_EXTERNAL_PLUGINS_PATH) -maxdepth 1 -mindepth 1 -type d); do\
		if test -f $$PLUGIN/Makefile -o -f $$PLUGIN/setup.py; then echo ">> LINK $$PLUGIN";\
			if test -f $$PLUGIN/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN PYTHON="$(PYTHON)" link &>/dev/null || echo ">> FAIL $$PLUGIN";\
			elif test -f $$PLUGIN/setup.py; then cd $$PLUGIN; $(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$PLUGIN"; fi;\
	done

man: man/avocado.1

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

.PHONY: source install clean check variables

# implicit rule/recipe for man page creation
%.1: %.rst
	rst2man $< $@
