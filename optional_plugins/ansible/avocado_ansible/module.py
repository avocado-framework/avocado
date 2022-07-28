from multiprocessing import Process, SimpleQueue

from avocado.core.nrunner.app import BaseRunnerApp
from avocado.core.nrunner.runner import BaseRunner
from avocado.core.utils import messages
from avocado.utils.process import CmdError, run


class AnsibleModuleRunner(BaseRunner):
    """Runner for dependencies of type ansible-module

    This runner handles download and verification.

    Runnable attributes usage:

     * kind: 'ansible-module'

     * uri: the name of the module

     * args: not used

     * kwargs: passed as arguments to ansible module
    """

    name = "ansible-module"
    description = f"Runner for dependencies of type {name}"

    def _run_ansible_module(self, runnable, queue):
        args = " ".join([f"{k}={v}" for k, v in runnable.kwargs.items()])
        if args:
            args_cmdline = f"-a '{args}'"
        else:
            args_cmdline = ""
        try:
            proc_result = run(f"ansible -m {runnable.uri} {args_cmdline} localhost")
            result = "pass"
            stdout = proc_result.stdout
            stderr = proc_result.stderr
        except CmdError as e:
            result = "fail"
            stdout = ""
            stderr = str(e)
        queue.put({"result": result, "stdout": stdout, "stderr": stderr})

    def run(self, runnable):
        yield messages.StartedMessage.get()

        if not runnable.uri:
            reason = "uri identifying the ansible module is required"
            yield messages.FinishedMessage.get("error", reason)
            return

        queue = SimpleQueue()
        process = Process(target=self._run_ansible_module, args=(runnable, queue))
        process.start()
        yield from self.running_loop(lambda: not queue.empty())

        status = queue.get()
        yield messages.StdoutMessage.get(status["stdout"])
        yield messages.StderrMessage.get(status["stderr"])
        yield messages.FinishedMessage.get(status["result"])


class RunnerApp(BaseRunnerApp):
    PROG_NAME = f"avocado-runner-{AnsibleModuleRunner.name}"
    PROG_DESCRIPTION = AnsibleModuleRunner.description
    RUNNABLE_KINDS_CAPABLE = [AnsibleModuleRunner.name]


def main():
    app = RunnerApp(print)
    app.run()


if __name__ == "__main__":
    main()
