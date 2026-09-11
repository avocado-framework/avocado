#!/usr/bin/env python3

import argparse
import atexit
import copy
import glob
import multiprocessing
import os
import platform
import re
import shutil
import sys
import tempfile
from importlib.metadata import distributions

SELFTESTS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPTIONAL_PLUGINS = {
    "ansible": "avocado-framework-plugin-ansible",
    "golang": "avocado-framework-plugin-golang",
    "html": "avocado-framework-plugin-result-html",
    "robot": "avocado-framework-plugin-robot",
    "varianter_cit": "avocado-framework-plugin-varianter-cit",
    "varianter_yaml_to_mux": "avocado-framework-plugin-varianter-yaml-to-mux",
}
SELFTEST_PLUGIN_DISTRIBUTIONS = {"magic", "avocado-rogue"}


def _distribution_name(distribution):
    """Return a normalized distribution name."""
    name = distribution.metadata.get("Name", "")
    return re.sub(r"[-_.]+", "-", name).lower()


def _external_plugins(allowed_distributions):
    """Return installed Avocado plugins that do not belong to this tree."""
    disabled = set()
    for distribution in distributions():
        if _distribution_name(distribution) in allowed_distributions:
            continue
        for entry_point in distribution.entry_points:
            if entry_point.group.startswith("avocado.plugins."):
                plugin_type = entry_point.group.removeprefix("avocado.plugins.")
                disabled.add(f"{plugin_type}.{entry_point.name}")
    return sorted(disabled)


def _disabled_plugin_checks_from_argv():
    """Read plugin exclusions before importing Avocado and its plugins."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--disable-plugin-checks", action="append", default=[])
    parsed, _ = parser.parse_known_args()
    return {
        plugin for value in parsed.disable_plugin_checks for plugin in value.split(",")
    }


def _setup_isolated_environment():
    """Keep source-tree selftests independent of the host installation if any."""
    disabled_plugin_checks = _disabled_plugin_checks_from_argv()
    enabled_optional_plugins = {
        name: distribution
        for name, distribution in OPTIONAL_PLUGINS.items()
        if name not in disabled_plugin_checks
    }
    python_paths = [
        SELFTESTS_ROOT,
        *(
            os.path.join(SELFTESTS_ROOT, "optional_plugins", plugin)
            for plugin in enabled_optional_plugins
        ),
    ]
    inherited_python_path = os.environ.get("PYTHONPATH")
    if inherited_python_path:
        inherited_paths = {
            os.path.abspath(path)
            for path in inherited_python_path.split(os.pathsep)
            if path
        }
        sys.path[:] = [
            path
            for path in sys.path
            if os.path.abspath(path) not in inherited_paths
            or os.path.abspath(path) == SELFTESTS_ROOT
        ]
    python_paths = list(dict.fromkeys(os.path.abspath(path) for path in python_paths))
    os.environ["PYTHONPATH"] = os.pathsep.join(python_paths)
    for path in reversed(python_paths):
        if path not in sys.path:
            sys.path.insert(0, path)

    # Settings treats VIRTUAL_ENV as both its system and user configuration
    # root. Pointing it at an empty temporary directory prevents /etc and
    # ~/.config from changing selftest behavior, and is inherited by every
    # runner and avocado subprocess started below.
    isolation_dir = tempfile.mkdtemp(prefix="selftests-config-")
    os.environ["VIRTUAL_ENV"] = isolation_dir
    config_dir = os.path.join(isolation_dir, "etc", "avocado")
    os.makedirs(config_dir)
    config_path = os.path.join(config_dir, "avocado.conf")
    with open(config_path, "w", encoding="utf-8") as config_file:
        allowed_distributions = {"avocado-framework"}
        allowed_distributions.update(enabled_optional_plugins.values())
        allowed_distributions.update(SELFTEST_PLUGIN_DISTRIBUTIONS)
        config_file.write(
            "[plugins]\n" f"disable = {_external_plugins(allowed_distributions)!r}\n"
        )
    atexit.register(shutil.rmtree, isolation_dir, ignore_errors=True)


_setup_isolated_environment()

from avocado import Test
from avocado.core import exit_codes
from avocado.core.job import Job
from avocado.core.suite import TestSuite
from avocado.utils import process
from selftests.utils import python_module_available

TEST_SIZE = {
    "static-checks": 3,
    "job-api-check-archive-file-exists": 1,
    "job-api-check-category-directory-exists": 1,
    "job-api-check-directory-exists": 2,
    "job-api-check-file-content": 9,
    "job-api-check-file-exists": 11,
    "job-api-check-output-file": 4,
    "job-api-check-tmp-directory-exists": 1,
    "nrunner-interface": 90,
    "nrunner-requirement": 28,
    "unit": 1046,
    "jobs": 11,
    "functional-parallel": 374,
    "functional-serial": 7,
    "optional-plugins": 0,
    "optional-plugins-golang": 2,
    "optional-plugins-html": 3,
    "optional-plugins-robot": 3,
    "optional-plugins-varianter_cit": 40,
    "optional-plugins-varianter_yaml_to_mux": 50,
    "vmimage-variants": 256,
    "vmimage-tests": 35,
    "pre-release": 18,
}


def _optional_plugin_checks_enabled(plugin_name, disabled_plugins):
    distribution_name = OPTIONAL_PLUGINS.get(plugin_name)
    return (
        distribution_name is not None
        and plugin_name not in disabled_plugins
        and python_module_available(distribution_name)
    )


SERIAL_SUITES = {
    "functional-serial",
    "nrunner-requirement",
    "pre-release",
    "vmimage-tests",
    "vmimage-variants",
}


def _set_max_parallel_tasks(suites, max_parallel_tasks):
    for suite in suites:
        suite.config["run.max_parallel_tasks"] = (
            1 if suite.name in SERIAL_SUITES else max_parallel_tasks
        )


class JobAPIFeaturesTest(Test):
    def check_directory_exists(self, path=None):
        """Check if a directory exists"""
        if path is None:
            path = os.path.join(self.latest_workdir, self.params.get("directory"))
        assert_func = self.get_assert_function()
        assert_func(os.path.isdir(path))

    def check_exit_code(self, exit_code):
        """Check if job ended with success."""
        expected_exit_code = self.params.get(
            "exit_code", default=exit_codes.AVOCADO_ALL_OK
        )
        self.assertEqual(expected_exit_code, exit_code)

    def check_file_exists(self, file_path):
        """Check if a file exists or not depending on the `assert_func`."""
        assert_func = self.get_assert_function()
        assert_func(os.path.exists(file_path))

    def check_file_content(self, file_path):
        """Check if `content` exists or not in a file."""
        content = self.params.get("content")
        assert_func = self.get_assert_function()
        regex = self.params.get("regex", default=False)
        assert_func(self.file_has_content(file_path, content, regex))

    def create_config(self, value=None):
        """Creates the Job config."""
        if value is None:
            value = self.params.get("value")
        reference = self.params.get("reference", default=["examples/tests/true"])
        config = {
            "core.show": ["none"],
            "run.results_dir": self.workdir,
            "resolver.references": reference,
        }
        namespace = self.params.get("namespace")
        config[namespace] = value
        extra_job_config = self.params.get("extra_job_config")
        if extra_job_config is not None:
            config.update(extra_job_config)

        return config

    @staticmethod
    def file_has_content(file_path, content, regex):
        """Check if a file has `content`."""
        if os.path.isfile(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for line in lines:
                if regex:
                    if re.match(content, line):
                        return True
                else:
                    if content in line:
                        return True
        return False

    def get_assert_function(self):
        """Return an assert function depending on the assert passed"""
        assert_option = self.params.get("assert")
        if assert_option:
            return self.assertTrue
        return self.assertFalse

    @property
    def latest_workdir(self):
        return os.path.join(self.workdir, "latest")

    def run_job(self):
        """Run a Job"""
        config = self.create_config()

        suite = TestSuite.from_config(config, "")

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()

        return result

    @property
    def workdir_file_path(self):
        file_name = self.params.get("file")
        return os.path.join(self.latest_workdir, file_name)

    def test_check_archive_file_exists(self):
        """Test to check the archive file was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()
            logdir = j.logdir

        # Asserts
        self.check_exit_code(result)
        archive_path = f"{logdir}.zip"
        self.check_file_exists(archive_path)

    def test_check_category_directory_exists(self):
        """Test to check if the category directory was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()
            logdir = j.logdir

        # Asserts
        self.check_exit_code(result)

        value = self.params.get("value")
        category_path = os.path.join(os.path.dirname(logdir), value)
        self.check_directory_exists(category_path)

    def test_check_directory_exists(self):
        """Test to check if a directory was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()

        # Asserts
        self.check_exit_code(result)
        self.check_directory_exists()

    def test_check_file_content(self):
        """Test to check if a file has the desired content."""
        result = self.run_job()

        # Asserts
        self.check_exit_code(result)
        self.check_file_content(self.workdir_file_path)

    def test_check_file_exists(self):
        """Test to check if a file was created."""
        result = self.run_job()

        # Asserts
        self.check_exit_code(result)
        self.check_file_exists(self.workdir_file_path)

    def test_check_output_file(self):
        """Test to check if the file passed as parameter was created."""
        config = self.create_config(self.workdir_file_path)

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()

        # Asserts
        self.check_exit_code(result)
        self.check_file_exists(self.workdir_file_path)

    def test_check_tmp_directory_exists(self):
        """Test to check if the temporary directory was created."""
        config = self.create_config()

        suite = TestSuite.from_config(config)

        # run the job
        with Job(config, [suite]) as j:
            result = j.run()
            tmpdir = j.tmpdir

        # Asserts
        self.check_exit_code(result)
        self.check_directory_exists(tmpdir)


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
The list of test availables for --skip and --select are:

  static-checks         Run static checks (isort, lint, etc)
  job-api               Run job API checks
  nrunner-interface     Run selftests/functional/nrunner_interface.py
  nrunner-requirement   Run selftests/functional/serial/requirements.py
  unit                  Run selftests/unit/
  jobs                  Run selftests/jobs/
  functional            Run selftests/functional/
  optional-plugins      Run optional_plugins/*/tests/
  vmimage               Run selftests/vmimage/ tests (tests first, then variants)
        """,
    )
    group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "-f",
        "--list-features",
        help="show the list of features tested by this test.",
        action="store_true",
    )
    group.add_argument(
        "--skip",
        help="Run all tests and skip listed tests",
        action="append",
        default=[],
    )
    group.add_argument(
        "--select",
        help="Do not run any test, only these listed after",
        action="append",
        default=[],
    )
    # Hidden argument to have the list of tests
    group.add_argument("--dict-tests", default={}, help=argparse.SUPPRESS)
    parser.add_argument(
        "--disable-plugin-checks",
        help="Disable checks for one or more plugins (by directory name), separated by comma",
        action="append",
        default=[],
    )
    parser.add_argument(
        "-j",
        "--max-parallel-tasks",
        type=int,
        help=(
            "Maximum tasks for each parallel suite. Suites that require serial "
            "execution remain limited to one task."
        ),
    )

    arg = parser.parse_args()
    if arg.max_parallel_tasks is not None and arg.max_parallel_tasks < 1:
        parser.error("--max-parallel-tasks must be greater than zero")
    return arg


def create_suite_job_api(args):  # pylint: disable=W0621
    suites = []

    def get_ref(method_short_name):
        return [f"{__file__}:JobAPIFeaturesTest.test_{method_short_name}"]

    # ========================================================================
    # Test if the archive file was created
    # ========================================================================
    config_check_archive_file_exists = {
        "resolver.references": get_ref("check_archive_file_exists"),
        "run.dict_variants.variant_id_keys": ["namespace", "value"],
        "run.dict_variants": [
            {"namespace": "run.results.archive", "value": True, "assert": True},
        ],
    }

    suites.append(
        TestSuite.from_config(
            config_check_archive_file_exists, "job-api-check-archive-file-exists"
        )
    )

    # ========================================================================
    # Test if the category directory was created
    # ========================================================================
    config_check_category_directory_exists = {
        "resolver.references": get_ref("check_category_directory_exists"),
        "run.dict_variants.variant_id_keys": ["namespace", "value"],
        "run.dict_variants": [
            {"namespace": "run.job_category", "value": "foo", "assert": True},
        ],
    }

    suites.append(
        TestSuite.from_config(
            config_check_category_directory_exists,
            "job-api-check-category-directory-exists",
        )
    )

    # ========================================================================
    # Test if a directory was created
    # ========================================================================
    config_check_directory_exists = {
        "resolver.references": get_ref("check_directory_exists"),
        "run.dict_variants.variant_id_keys": ["namespace", "value"],
        "run.dict_variants": [
            {
                "namespace": "sysinfo.collect.enabled",
                "value": True,
                "directory": "sysinfo",
                "assert": True,
            },
            {
                "namespace": "sysinfo.collect.enabled",
                "value": False,
                "directory": "sysinfo",
                "assert": False,
            },
        ],
    }

    suites.append(
        TestSuite.from_config(
            config_check_directory_exists, "job-api-check-directory-exists"
        )
    )

    # ========================================================================
    # Test the content of a file
    # ========================================================================
    config_check_file_content = {
        "resolver.references": get_ref("check_file_content"),
        "run.dict_variants.variant_id_keys": ["namespace", "value", "file"],
        "run.dict_variants": [
            # finding the correct 'content' here is trick because any
            # simple string is added to the variant file name and is
            # found in the log file.
            # Using DEBUG| makes the variant name have DEBUG_, working
            # fine here.
            {
                "namespace": "job.output.loglevel",
                "value": "INFO",
                "file": "job.log",
                "content": r"DEBUG\| Test metadata:$",
                "assert": False,
                "regex": True,
            },
            {
                "namespace": "job.run.result.tap.include_logs",
                "value": True,
                "file": "results.tap",
                "reference": ["examples/tests/passtest.py:PassTest.test"],
                "content": "PASS 1-examples/tests/passtest.py:PassTest.test",
                "assert": True,
            },
            {
                "namespace": "job.run.result.tap.include_logs",
                "value": False,
                "file": "results.tap",
                "content": "Command 'examples/tests/true' finished with 0",
                "assert": False,
            },
            {
                "namespace": "job.run.result.xunit.job_name",
                "value": "foo",
                "file": "results.xml",
                "content": 'name="foo"',
                "assert": True,
            },
            {
                "namespace": "job.run.result.xunit.max_test_log_chars",
                "value": 1,
                "file": "results.xml",
                "content": "--[ CUT DUE TO XML PER TEST LIMIT ]--",
                "assert": True,
                "reference": ["examples/tests/failtest.py:FailTest.test"],
                "exit_code": 1,
            },
            {
                "namespace": "run.failfast",
                "value": True,
                "file": "results.json",
                "content": '"skip": 1',
                "assert": True,
                "reference": ["examples/tests/false", "examples/tests/true"],
                "exit_code": 9,
                "extra_job_config": {"run.max_parallel_tasks": 1},
            },
            {
                "namespace": "run.ignore_missing_references",
                "value": "on",
                "file": "results.json",
                "content": '"pass": 1',
                "assert": True,
                "reference": ["examples/tests/true", "foo"],
            },
            {
                "namespace": "run.unique_job_id",
                "value": "abcdefghi",
                "file": "job.log",
                "content": "Job ID: abcdefghi",
                "assert": True,
            },
            {
                "namespace": "job.run.timeout",
                "value": 1,
                "reference": ["examples/tests/sleeptenmin.py"],
                "file": "job.log",
                "content": "Test interrupted: Timeout reached",
                "assert": True,
                "exit_code": 8,
            },
        ],
    }

    suites.append(
        TestSuite.from_config(config_check_file_content, "job-api-check-file-content")
    )

    # ========================================================================
    # Test if the result file was created
    # ========================================================================
    config_check_file_exists = {
        "resolver.references": get_ref("check_file_exists"),
        "run.dict_variants.variant_id_keys": ["namespace", "value"],
        "run.dict_variants": [
            {
                "namespace": "job.run.result.json.enabled",
                "value": True,
                "file": "results.json",
                "assert": True,
            },
            {
                "namespace": "job.run.result.json.enabled",
                "value": False,
                "file": "results.json",
                "assert": False,
            },
            {
                "namespace": "job.run.result.tap.enabled",
                "value": True,
                "file": "results.tap",
                "assert": True,
            },
            {
                "namespace": "job.run.result.tap.enabled",
                "value": False,
                "file": "results.tap",
                "assert": False,
            },
            {
                "namespace": "job.run.result.xunit.enabled",
                "value": True,
                "file": "results.xml",
                "assert": True,
            },
            {
                "namespace": "job.run.result.xunit.enabled",
                "value": False,
                "file": "results.xml",
                "assert": False,
            },
            {
                "namespace": "run.dry_run.enabled",
                "value": True,
                "file": "job.log",
                "assert": False,
            },
            {
                "namespace": "run.dry_run.no_cleanup",
                "value": True,
                "file": "job.log",
                "assert": True,
            },
            {
                "namespace": "plugins.disable",
                "value": ["result.xunit"],
                "file": "result.xml",
                "assert": False,
            },
        ],
    }

    if (
        python_module_available("avocado-framework-plugin-result-html")
        and "html" not in args.disable_plugin_checks
    ):

        config_check_file_exists["run.dict_variants"].append(
            {
                "namespace": "job.run.result.html.enabled",
                "value": True,
                "file": "results.html",
                "assert": True,
            }
        )

        config_check_file_exists["run.dict_variants"].append(
            {
                "namespace": "job.run.result.html.enabled",
                "value": False,
                "file": "results.html",
                "assert": False,
            }
        )

    suites.append(
        TestSuite.from_config(config_check_file_exists, "job-api-check-file-exists")
    )

    # ========================================================================
    # Test if a file was created
    # ========================================================================
    config_check_output_file = {
        "resolver.references": get_ref("check_output_file"),
        "run.dict_variants.variant_id_keys": ["namespace", "file"],
        "run.dict_variants": [
            {
                "namespace": "job.run.result.json.output",
                "file": "custom.json",
                "assert": True,
            },
            # https://github.com/avocado-framework/avocado/issues/4034
            {
                "namespace": "job.run.result.tap.output",
                "file": "custom.tap",
                "assert": True,
            },
            {
                "namespace": "job.run.result.xunit.output",
                "file": "custom.xml",
                "assert": True,
            },
        ],
    }

    if (
        python_module_available("avocado-framework-plugin-result-html")
        and "html" not in args.disable_plugin_checks
    ):

        config_check_output_file["run.dict_variants"].append(
            {
                "namespace": "job.run.result.html.output",
                "file": "custom.html",
                "assert": True,
            }
        )

    suites.append(
        TestSuite.from_config(config_check_output_file, "job-api-check-output-file")
    )

    # ========================================================================
    # Test if the temporary directory was created
    # ========================================================================
    config_check_tmp_directory_exists = {
        "resolver.references": get_ref("check_tmp_directory_exists"),
        "run.dict_variants.variant_id_keys": ["namespace", "value"],
        "run.dict_variants": [
            {"namespace": "run.keep_tmp", "value": True, "assert": True},
        ],
    }

    suites.append(
        TestSuite.from_config(
            config_check_tmp_directory_exists, "job-api-check-tmp-directory-exists"
        )
    )
    return suites


def create_suites(args):  # pylint: disable=W0621
    suites = []
    config_check = {"run.ignore_missing_references": True}

    if args.dict_tests["static-checks"]:
        config_check_static = copy.copy(config_check)
        config_check_static["resolver.references"] = glob.glob("selftests/*.sh")
        suites.append(TestSuite.from_config(config_check_static, "static-checks"))

    # ========================================================================
    # Run nrunner interface checks for all available runners
    # ========================================================================
    nrunner_interface_size = 10
    config_nrunner_interface = {
        "resolver.references": ["selftests/functional/nrunner_interface.py"],
        "run.dict_variants.variant_id_keys": ["runner"],
        "run.dict_variants": [
            {
                "runner": "avocado-runner-dry-run",
            },
            {
                "runner": "avocado-runner-noop",
            },
            {
                "runner": "avocado-runner-exec-test",
            },
            {
                "runner": "avocado-runner-python-unittest",
            },
            {
                "runner": "avocado-runner-avocado-instrumented",
            },
            {
                "runner": "avocado-runner-tap",
            },
            {
                "runner": "avocado-runner-podman-image",
            },
            {
                "runner": "avocado-runner-pip",
            },
            {
                "runner": "avocado-runner-vmimage",
            },
        ],
    }

    if (
        python_module_available("avocado-framework-plugin-golang")
        and shutil.which("avocado-runner-golang") is not None
        and "golang" not in args.disable_plugin_checks
    ):
        config_nrunner_interface["run.dict_variants"].append(
            {
                "runner": "avocado-runner-golang",
            }
        )
        TEST_SIZE["nrunner-interface"] += nrunner_interface_size

    if (
        python_module_available("avocado-framework-plugin-robot")
        and shutil.which("avocado-runner-robot") is not None
        and "robot" not in args.disable_plugin_checks
    ):
        config_nrunner_interface["run.dict_variants"].append(
            {
                "runner": "avocado-runner-robot",
            }
        )
        TEST_SIZE["nrunner-interface"] += nrunner_interface_size

    if (
        python_module_available("avocado-framework-plugin-ansible")
        and shutil.which("avocado-runner-ansible-module") is not None
        and "ansible" not in args.disable_plugin_checks
    ):
        config_nrunner_interface["run.dict_variants"].append(
            {
                "runner": "avocado-runner-ansible-module",
            }
        )
        TEST_SIZE["nrunner-interface"] += nrunner_interface_size

    if args.dict_tests["nrunner-interface"]:
        suites.append(
            TestSuite.from_config(config_nrunner_interface, "nrunner-interface")
        )

    # ========================================================================
    # Run functional requirement tests
    # ========================================================================
    config_nrunner_requirement = {
        "resolver.references": ["selftests/functional/serial/requirements.py"],
        "run.max_parallel_tasks": 1,
        "run.dict_variants": [
            {"spawner": "process"},
            {"spawner": "podman"},
            {"spawner": "lxc"},
            {"spawner": "remote"},
        ],
    }

    if args.dict_tests["nrunner-requirement"]:
        suites.append(
            TestSuite.from_config(config_nrunner_requirement, "nrunner-requirement")
        )

    # ========================================================================
    # Run all static checks, unit and functional tests
    # ========================================================================

    if args.dict_tests["unit"]:
        config_check_unit = copy.copy(config_check)
        config_check_unit["resolver.references"] = ["selftests/unit/"]
        suites.append(TestSuite.from_config(config_check_unit, "unit"))

    if args.dict_tests["jobs"]:
        config_check_jobs = copy.copy(config_check)
        config_check_jobs["resolver.references"] = ["selftests/jobs/"]
        suites.append(TestSuite.from_config(config_check_jobs, "jobs"))

    if args.dict_tests["functional"]:
        functional_path = os.path.join("selftests", "functional")
        references = glob.glob(os.path.join(functional_path, "*.py"))
        references.extend(
            [
                os.path.join(functional_path, "utils"),
                os.path.join(functional_path, "plugin"),
            ]
        )
        config_check_functional_parallel = copy.copy(config_check)
        config_check_functional_parallel["resolver.references"] = references
        suites.append(
            TestSuite.from_config(
                config_check_functional_parallel, "functional-parallel"
            )
        )

        config_check_functional_serial = copy.copy(config_check)
        config_check_functional_serial["resolver.references"] = [
            "selftests/functional/serial/"
        ]
        config_check_functional_serial["run.max_parallel_tasks"] = 1
        suites.append(
            TestSuite.from_config(config_check_functional_serial, "functional-serial")
        )

    if args.dict_tests["optional-plugins"]:
        config_check_optional = copy.copy(config_check)
        config_check_optional["resolver.references"] = []
        for optional_plugin in glob.glob("optional_plugins/*"):
            plugin_name = os.path.basename(optional_plugin)
            if _optional_plugin_checks_enabled(plugin_name, args.disable_plugin_checks):
                pattern = f"{optional_plugin}/tests/*"
                config_check_optional["resolver.references"] += glob.glob(pattern)

        suites.append(TestSuite.from_config(config_check_optional, "optional-plugins"))

    test_dir = os.path.join("selftests", "vmimage")

    # Combined vmimage option - tests first, then variants
    if args.dict_tests.get("vmimage"):
        # First suite: vmimage tests
        vmimage_tests_config = {
            "resolver.references": [
                os.path.join(test_dir, "tests"),
            ],
            "run.max_parallel_tasks": 1,
        }
        suites.append(TestSuite.from_config(vmimage_tests_config, "vmimage-tests"))

        # Second suite: vmimage variants
        vmimage_variants_config = {
            "resolver.references": [
                os.path.join(test_dir, "variants", "vmimage.py"),
            ],
            "yaml_to_mux.files": [
                os.path.join(test_dir, "variants", "vmimage.py.data", "variants.yml")
            ],
            "run.max_parallel_tasks": 1,
        }
        suites.append(
            TestSuite.from_config(vmimage_variants_config, "vmimage-variants")
        )

    if args.dict_tests.get("pre-release"):
        os.environ["AVOCADO_CHECK_LEVEL"] = "3"
        pre_release_config = {
            "resolver.references": [
                os.path.join("selftests", "unit"),
                os.path.join("selftests", "functional"),
            ],
            "filter.by_tags.tags": ["parallel:1"],
            "run.max_parallel_tasks": 1,
        }
        suites.append(TestSuite.from_config(pre_release_config, "pre-release"))

    return suites


def main(args):  # pylint: disable=W0621

    args.disable_plugin_checks = [
        plugin for value in args.disable_plugin_checks for plugin in value.split(",")
    ]
    args.select = [item for value in args.select for item in value.split(",")]
    args.skip = [item for value in args.skip for item in value.split(",")]

    args.dict_tests = {
        "static-checks": False,
        "job-api": False,
        "nrunner-interface": False,
        "nrunner-requirement": False,
        "unit": False,
        "jobs": False,
        "functional": False,
        "optional-plugins": False,
    }
    select_only = {
        "vmimage": False,
        "pre-release": False,
    }

    optional_plugins_size = 0
    for plugin_name in OPTIONAL_PLUGINS:
        size_key = f"optional-plugins-{plugin_name}"
        if size_key in TEST_SIZE and _optional_plugin_checks_enabled(
            plugin_name, args.disable_plugin_checks
        ):
            optional_plugins_size += TEST_SIZE[size_key]
    TEST_SIZE["optional-plugins"] = optional_plugins_size

    # Print features covered in this test
    if args.list_features:
        suites = create_suites(args)
        suites += create_suite_job_api(args)
        features = []
        for suite in suites:
            for variants in suite.config["run.dict_variants"]:
                if variants.get("namespace"):
                    features.append(variants["namespace"])

        unique_features = sorted(set(features))
        print(f"Features covered ({len(unique_features)}):")
        print("\n".join(unique_features))
        exit(0)

    # Will only run the test you select, --select must be followed by list of tests
    elif args.select:
        for elem in args.select:
            if elem not in args.dict_tests.keys() and elem not in select_only.keys():
                print(elem, "is not in the list of valid tests.")
                exit(0)
            else:
                args.dict_tests[elem] = True

    # Will run all the tests except these you skip, --skip must be followed by list of tests
    elif args.skip:
        # Make all the values True, so later we set to False the tests we don't want to run
        args.dict_tests = {x: True for x in args.dict_tests}

        for elem in args.skip:
            if elem not in args.dict_tests.keys():
                print(elem, "is not in the list of valid tests.")
                exit(0)
            else:
                args.dict_tests[elem] = False

    # If no option was selected, run all tests!
    elif not (args.skip or args.select):
        print("No test were selected to run, running all of them.")
        args.dict_tests = {x: True for x in args.dict_tests}

    else:
        print("Something went wrong, please report a bug!")
        exit(1)

    suites = create_suites(args)
    if args.dict_tests["job-api"]:
        suites += create_suite_job_api(args)

    # ========================================================================
    # Job execution
    # ========================================================================
    config = {
        "run.job_category": "avocado-selftests",
        "job.output.testlogs.statuses": ["FAIL", "ERROR", "INTERRUPT"],
    }

    # Workaround for travis problem on arm64 - https://github.com/avocado-framework/avocado/issues/4768
    if platform.machine() == "aarch64":
        max_parallel = int(multiprocessing.cpu_count() / 2)
        for suite in suites:
            if suite.name == "functional-parallel":
                suite.config["run.max_parallel_tasks"] = max_parallel

    max_parallel_tasks = getattr(args, "max_parallel_tasks", None)
    if max_parallel_tasks is not None:
        _set_max_parallel_tasks(suites, max_parallel_tasks)

    with Job(config, suites) as j:
        pre_job_test_result_dirs = set(os.listdir(os.path.dirname(j.logdir)))
        exit_code = j.run()
        post_job_test_result_dirs = set(os.listdir(os.path.dirname(j.logdir)))
        if len(pre_job_test_result_dirs) != len(post_job_test_result_dirs):
            if exit_code == 0:
                exit_code = 1
            print("check.py didn't clean test results.")
            print("uncleaned directories:")
            print(post_job_test_result_dirs.difference(pre_job_test_result_dirs))
        for suite in j.test_suites:
            if suite.size != TEST_SIZE[suite.name]:
                if exit_code == 0:
                    exit_code = 1
                print(
                    f"suite {suite.name} doesn't have {TEST_SIZE[suite.name]} tests"
                    f" it has {suite.size}."
                )
                print(
                    "If you made some changes into selftests please update `TEST_SIZE`"
                    " variable in `check.py`. If you haven't done any changes to"
                    " selftests this behavior is an ERROR, and it needs to be fixed."
                )

    # tmp dirs clean up check
    process.run(f"{sys.executable} selftests/check_tmp_dirs")
    return exit_code


if __name__ == "__main__":
    args = parse_args()
    sys.exit(main(args))
