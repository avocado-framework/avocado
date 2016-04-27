# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2015
# Author: Cleber Rosa <cleber@redhat.com>

"""Extensions/plugins dispatchers."""

import sys

from stevedore import ExtensionManager


class Dispatcher(ExtensionManager):

    """
    Base dispatcher for various extension types
    """

    def __init__(self, namespace):
        self.load_failures = []
        super(Dispatcher, self).__init__(namespace=namespace,
                                         invoke_on_load=True,
                                         on_load_failure_callback=self.store_load_failure,
                                         propagate_map_exceptions=True)

    @staticmethod
    def store_load_failure(manager, entrypoint, exception):
        manager.load_failures.append((entrypoint, exception))


class CLIDispatcher(Dispatcher):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli'
    """

    def __init__(self):
        super(CLIDispatcher, self).__init__('avocado.plugins.cli')


class CLICmdDispatcher(Dispatcher):

    """
    Calls extensions on configure/run

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.cli.cmd'
    """

    def __init__(self):
        super(CLICmdDispatcher, self).__init__('avocado.plugins.cli.cmd')


class JobPrePostDispatcher(Dispatcher):

    """
    Calls extensions before Job execution

    Automatically adds all the extension with entry points registered under
    'avocado.plugins.job.prepost'
    """

    def __init__(self):
        super(JobPrePostDispatcher, self).__init__('avocado.plugins.job.prepost')

    def map_methods(self, method_name, job):
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    method(job)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:
                job.log.error('Error running method "%s" of plugin "%s": %s',
                              method_name, ext.name, sys.exc_info()[1])
