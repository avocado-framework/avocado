from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.registry import RUNNERS_REGISTRY_PYTHON_CLASS
from avocado.core.runners.avocado_instrumented import \
    AvocadoInstrumentedTestRunner
from avocado.core.runners.dry_run import DryRunRunner
from avocado.core.runners.exec_test import ExecTestRunner
from avocado.core.runners.noop import NoOpRunner
from avocado.core.runners.python_unittest import PythonUnittestRunner
from avocado.core.runners.requirement_asset import RequirementAssetRunner
from avocado.core.runners.requirement_package import RequirementPackageRunner
from avocado.core.runners.sysinfo import SysinfoRunner
from avocado.core.runners.tap import TAPRunner

RUNNERS_REGISTRY_PYTHON_CLASS['dry-run'] = DryRunRunner
RUNNERS_REGISTRY_PYTHON_CLASS['noop'] = NoOpRunner
RUNNERS_REGISTRY_PYTHON_CLASS['exec-test'] = ExecTestRunner
RUNNERS_REGISTRY_PYTHON_CLASS['python-unittest'] = PythonUnittestRunner
RUNNERS_REGISTRY_PYTHON_CLASS['avocado-instrumented'] = AvocadoInstrumentedTestRunner
RUNNERS_REGISTRY_PYTHON_CLASS['requirement-asset'] = RequirementAssetRunner
RUNNERS_REGISTRY_PYTHON_CLASS['requirement-package'] = RequirementPackageRunner
RUNNERS_REGISTRY_PYTHON_CLASS['sysinfo'] = SysinfoRunner
RUNNERS_REGISTRY_PYTHON_CLASS['tap'] = TAPRunner


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner'
    PROG_DESCRIPTION = 'nrunner base application'
    RUNNABLE_KINDS_CAPABLE = RUNNERS_REGISTRY_PYTHON_CLASS


def main(app_class=RunnerApp):
    app = app_class(print)
    app.run()


if __name__ == '__main__':
    main()
