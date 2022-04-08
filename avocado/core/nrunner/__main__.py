from avocado.core.nrunner.app import BaseRunnerApp


class RunnerApp(BaseRunnerApp):
    PROG_NAME = 'avocado-runner'
    PROG_DESCRIPTION = 'nrunner base application'
    RUNNABLE_KINDS_CAPABLE = ['avocado-instrumented',
                              'dry-run',
                              'exec-test',
                              'noop',
                              'python-unittest',
                              'asset',
                              'package',
                              'sysinfo',
                              'tap']


def main(app_class=RunnerApp):
    app = app_class(print)
    app.run()


if __name__ == '__main__':
    main()
