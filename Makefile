PYTHON=$(shell which python 2>/dev/null || which python3 2>/dev/null)
VERSION=$(shell $(PYTHON) setup.py --version 2>/dev/null)
PYTHON_DEVELOP_ARGS=$(shell if ($(PYTHON) setup.py develop --help 2>/dev/null | grep -q '\-\-user'); then echo "--user"; else echo ""; fi)
DESTDIR=/
AVOCADO_DIRNAME=$(shell echo $${PWD\#\#*/})
AVOCADO_EXTERNAL_PLUGINS=$(filter-out ../$(AVOCADO_DIRNAME), $(shell find ../ -maxdepth 1 -mindepth 1 -type d))
# List of optional plugins that have to be in setup in a giver order
# because there may be depedencies between plugins
AVOCADO_OPTIONAL_PLUGINS_ORDERED="./optional_plugins/runner_remote"
# Other optional plugins found in "optional_plugins" directory
AVOCADO_OPTIONAL_PLUGINS_OTHERS=$(shell find ./optional_plugins -maxdepth 1 -mindepth 1 -type d)
# Unique list of optional plugins
AVOCADO_OPTIONAL_PLUGINS=$(shell (echo "$(AVOCADO_OPTIONAL_PLUGINS_ORDERED) $(AVOCADO_OPTIONAL_PLUGINS_OTHERS)" | tr ' ' '\n' | awk '!a[$$0]++'))
AVOCADO_PLUGINS=$(AVOCADO_OPTIONAL_PLUGINS) $(AVOCADO_EXTERNAL_PLUGINS)
RELEASE_COMMIT=$(shell git log --pretty=format:'%H' -n 1 $(VERSION))
RELEASE_SHORT_COMMIT=$(shell git log --pretty=format:'%h' -n 1 $(VERSION))
COMMIT=$(shell git log --pretty=format:'%H' -n 1)
COMMIT_DATE=$(shell git log --pretty='format:%cd' --date='format:%Y%m%d' -n 1)
SHORT_COMMIT=$(shell git log --pretty=format:'%h' -n 1)
MOCK_CONFIG=default
ARCHIVE_BASE_NAME=avocado
PYTHON_MODULE_NAME=avocado-framework
RPM_BASE_NAME=python-avocado

include Makefile.include

all:
	@echo
	@echo "Development related targets:"
	@echo "check:          Runs tree static check, unittests and fast functional tests"
	@echo "check-full:     Runs tree static check, and all unittests and functional tests"
	@echo "develop:        Runs 'python setup.py --develop' on this tree alone"
	@echo "link:           Runs 'python setup.py --develop' in all subprojects and links the needed resources"
	@echo "clean:          Get rid of scratch, byte files and removes the links to other subprojects"
	@echo "selfcheck:      Runs tree static check, unittests and functional tests using Avocado itself"
	@echo "spell:          Runs spell checker on comments and docstrings (requires python-enchant)"
	@echo
	@echo "Package requirements related targets"
	@echo "requirements:            Install runtime requirements"
	@echo "requirements-selftests:  Install runtime and selftests requirements"
	@echo "requirements-plugins:    Install plugins requirements"
	@echo
	@echo "Platform independent distribution/installation related targets:"
	@echo "source:   Create source package"
	@echo "install:  Install on local system"
	@echo "man:      Generate the avocado man page"
	@echo
	@echo "RPM related targets:"
	@echo "srpm:  Generate a source RPM package (.srpm)"
	@echo "rpm:   Generate binary RPMs"
	@echo
	@echo "Release related targets:"
	@echo "source-release:     Create source package for the latest tagged release"
	@echo "srpm-release:       Generate a source RPM package (.srpm) for the latest tagged release"
	@echo "rpm-release:        Generate binary RPMs for the latest tagged release"
	@echo "propagate-version:  Propagate './VERSION' to all plugins/modules"
	@echo

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
	$(PYTHON) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean || true
	rm -rf build/ MANIFEST BUILD BUILDROOT SPECS RPMS SRPMS SOURCES PYPI_UPLOAD
	rm -f man/avocado.1
	rm -f man/avocado-rest-client.1
	rm -rf docs/build
	find docs/source/api/ -name '*.rst' -delete
	for PLUGIN in $(AVOCADO_PLUGINS); do\
		if test -f $$PLUGIN/Makefile -o -f $$PLUGIN/setup.py; then echo ">> UNLINK $$PLUGIN";\
			if test -f $$PLUGIN/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN unlink &>/dev/null || echo ">> FAIL $$PLUGIN";\
			elif test -f $$PLUGIN/setup.py; then cd $$PLUGIN; $(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$PLUGIN"; fi;\
	done
	$(PYTHON) setup.py develop --uninstall $(PYTHON_DEVELOP_ARGS)
	rm -rf avocado_framework.egg-info
	rm -rf /var/tmp/avocado*
	rm -rf /tmp/avocado*
	find . -name '*.pyc' -delete
	find $(AVOCADO_OPTIONAL_PLUGINS) -name '*.egg-info' -exec rm -r {} +

requirements-plugins: requirements
	for PLUGIN in $(AVOCADO_PLUGINS);do\
		if test -f $$PLUGIN/Makefile; then echo ">> REQUIREMENTS (Makefile) $$PLUGIN"; AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN requirements &>/dev/null;\
		elif test -f $$PLUGIN/requirements.txt; then echo ">> REQUIREMENTS (requirements.txt) $$PLUGIN"; pip install $(PYTHON_DEVELOP_ARGS) -r $$PLUGIN/requirements.txt;\
		else echo ">> SKIP $$PLUGIN";\
		fi;\
	done;

smokecheck: clean develop
	./scripts/avocado run passtest.py

check: clean develop modules_boundaries
	# Unless manually set, this is equivalent to AVOCADO_CHECK_LEVEL=0
	selftests/checkall
	selftests/check_tmp_dirs

check-full: clean develop modules_boundaries
	AVOCADO_CHECK_LEVEL=2 selftests/checkall
	selftests/check_tmp_dirs

selfcheck: clean modules_boundaries develop
	AVOCADO_SELF_CHECK=1 selftests/checkall
	selftests/check_tmp_dirs

modules_boundaries:
	selftests/modules_boundaries

develop:
	$(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS)
	for PLUGIN in $(AVOCADO_OPTIONAL_PLUGINS); do\
		if test -f $$PLUGIN/Makefile -o -f $$PLUGIN/setup.py; then echo ">> LINK $$PLUGIN";\
			if test -f $$PLUGIN/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN link &>/dev/null;\
			elif test -f $$PLUGIN/setup.py; then cd $$PLUGIN; $(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$PLUGIN"; fi;\
	done

link: develop
	for PLUGIN in $(AVOCADO_EXTERNAL_PLUGINS); do\
		if test -f $$PLUGIN/Makefile -o -f $$PLUGIN/setup.py; then echo ">> LINK $$PLUGIN";\
			if test -f $$PLUGIN/Makefile; then AVOCADO_DIRNAME=$(AVOCADO_DIRNAME) make -C $$PLUGIN link &>/dev/null || echo ">> FAIL $$PLUGIN";\
			elif test -f $$PLUGIN/setup.py; then cd $$PLUGIN; $(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS); cd -; fi;\
		else echo ">> SKIP $$PLUGIN"; fi;\
	done

spell:
	pylint --errors-only --disable=all --enable=spelling --spelling-dict=en_US --spelling-private-dict-file=spell.ignore * && echo OK

man: man/avocado.1 man/avocado-rest-client.1

variables:
	@echo "PYTHON: $(PYTHON)"
	@echo "VERSION: $(VERSION)"
	@echo "PYTHON_DEVELOP_ARGS: $(PYTHON_DEVELOP_ARGS)"
	@echo "DESTDIR: $(DESTDIR)"
	@echo "AVOCADO_DIRNAME: $(AVOCADO_DIRNAME)"
	@echo "AVOCADO_EXTERNAL_PLUGINS: $(AVOCADO_EXTERNAL_PLUGINS)"
	@echo "AVOCADO_OPTIONAL_PLUGINS_ORDERED: $(AVOCADO_OPTIONAL_PLUGINS_ORDERED)"
	@echo "AVOCADO_OPTIONAL_PLUGINS_OTHERS: $(AVOCADO_OPTIONAL_PLUGINS_OTHERS)"
	@echo "AVOCADO_OPTIONAL_PLUGINS: $(AVOCADO_OPTIONAL_PLUGINS)"
	@echo "AVOCADO_PLUGINS: $(AVOCADO_PLUGINS)"
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
	for DIR in $(AVOCADO_PLUGINS); do\
		if test -f "$$DIR/VERSION"; then\
			echo ">> Updating $$DIR"; echo "$(VERSION)" > "$$DIR/VERSION";\
		else echo ">> Skipping $$DIR"; fi;\
	done

.PHONY: source install clean check link variables

# implicit rule/recipe for man page creation
%.1: %.rst
	rst2man $< $@
