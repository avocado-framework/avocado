all:
	@echo
	@echo "Development related targets:"
	@echo "check:             Runs tree static check, unittests and fast functional tests"
	@echo "smokecheck:        Runs the simplest possible avocado test execution"
	@echo "develop:           Runs 'python setup.py --develop' on this tree alone"
	@echo "develop-external:  Install Avocado's external plugins in develop mode."
	@echo "                   You need to set AVOCADO_EXTERNAL_PLUGINS_PATH"
	@echo "develop-plugins:   Install all optional plugins in develop mode"
	@echo "develop-plugin:    Install a specific optional plugin (use PLUGIN=name)"
	@echo "clean:             Get rid of build scratch from this project and subprojects"
	@echo "variables:         Show the value of variables as defined in this Makefile or"
	@echo "                   given as input to make"
	@echo
	@echo "Package requirements related targets"
	@echo "requirements-dev:      Install development requirements"
	@echo "requirements-static-checks:      Install development requirements for static checks"
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
	@echo "Cleaning build artifacts and cache files..."
	rm -rf build/ dist/ *.egg-info PYPI_UPLOAD EGG_UPLOAD
	rm -f man/avocado.1
	rm -rf docs/build
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf /tmp/.avocado-* /var/tmp/.avocado-* 2>/dev/null || true
	find docs/source/api -type f -name "*.rst" -delete 2>/dev/null || true
	@echo "Cleaning optional plugins..."
	@for plugin in optional_plugins/*/; do \
		if [ -d "$$plugin" ]; then \
			echo "  Cleaning $$plugin"; \
			rm -rf "$$plugin/build" "$$plugin/dist" "$$plugin"/*.egg-info 2>/dev/null || true; \
			find "$$plugin" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true; \
			find "$$plugin" -type f -name "*.pyc" -delete 2>/dev/null || true; \
		fi; \
	done
	@echo "Cleaning example plugins..."
	@for plugin in examples/plugins/tests/*/; do \
		if [ -d "$$plugin" ]; then \
			echo "  Cleaning $$plugin"; \
			rm -rf "$$plugin/build" "$$plugin/dist" "$$plugin"/*.egg-info 2>/dev/null || true; \
			find "$$plugin" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true; \
			find "$$plugin" -type f -name "*.pyc" -delete 2>/dev/null || true; \
		fi; \
	done
	@echo "Clean complete."

install:
	$(PYTHON) -m pip install . --root $(DESTDIR) $(COMPILE)

uninstall:
	$(PYTHON) -m pip uninstall -y avocado-framework

requirements-dev: pip
	$(PYTHON) -m pip install -r requirements-dev.txt $(PYTHON_DEVELOP_ARGS)

requirements-static-checks: pip
	$(PYTHON) -m pip install -r static-checks/requirements.txt $(PYTHON_DEVELOP_ARGS)

smokecheck: clean uninstall develop
	$(PYTHON) -m avocado run examples/tests/passtest.py

check: clean uninstall develop
	# Unless manually set, this is equivalent to AVOCADO_CHECK_LEVEL=0
	$(PYTHON) -m selftests.check

develop:
	$(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS)

develop-external:
ifndef AVOCADO_EXTERNAL_PLUGINS_PATH
	$(error AVOCADO_EXTERNAL_PLUGINS_PATH is not defined)
endif
	$(PYTHON) setup.py develop $(PYTHON_DEVELOP_ARGS) --external

develop-plugins:
	@echo "Installing all optional plugins in develop mode..."
	@for plugin in $(AVOCADO_OPTIONAL_PLUGINS); do \
		echo "Installing $$plugin..."; \
		$(PYTHON) -m pip install -e "$$plugin" $(PYTHON_DEVELOP_ARGS); \
	done
	@echo "All plugins installed."

develop-plugin:
ifndef PLUGIN
	$(error PLUGIN is not defined. Usage: make develop-plugin PLUGIN=html)
endif
	@echo "Installing plugin: $(PLUGIN)..."
	$(PYTHON) -m pip install -e "optional_plugins/$(PLUGIN)" $(PYTHON_DEVELOP_ARGS)

man: man/avocado.1

%.1: %.rst
	@if command -v rst2man >/dev/null 2>&1; then \
		rst2man man/avocado.rst man/avocado.1; \
	else \
		echo "ERROR: rst2man not found, cannot build manpage"; \
		exit 1; \
	fi

variables:
	@echo "PYTHON: $(PYTHON)"
	@echo "VERSION: $(VERSION)"
	@echo "PYTHON_DEVELOP_ARGS: $(PYTHON_DEVELOP_ARGS)"
	@echo "DESTDIR: $(DESTDIR)"
	@echo "AVOCADO_DIRNAME: $(AVOCADO_DIRNAME)"
	@echo "AVOCADO_OPTIONAL_PLUGINS: $(AVOCADO_OPTIONAL_PLUGINS)"

.PHONY: pip install clean uninstall requirements-dev smokecheck check develop develop-external develop-plugins develop-plugin variables man
