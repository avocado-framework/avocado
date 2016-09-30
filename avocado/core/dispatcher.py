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

from stevedore import EnabledExtensionManager

from .settings import settings


class Dispatcher(EnabledExtensionManager):

    """
    Base dispatcher for various extension types
    """

    def __init__(self, namespace):
        self.load_failures = []
        super(Dispatcher, self).__init__(namespace=namespace,
                                         check_func=self.enabled,
                                         invoke_on_load=True,
                                         on_load_failure_callback=self.store_load_failure,
                                         propagate_map_exceptions=True)

    def enabled(self, extension):
        namespace_prefix = 'avocado.plugins.'
        if self.namespace.startswith(namespace_prefix):
            namespace = self.namespace[len(namespace_prefix):]
        else:
            namespace = self.namespace
        disabled = settings.get_value('plugins', 'disable', key_type=list)
        fqn = "%s.%s" % (namespace, extension.entry_point.name)
        return fqn not in disabled

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

    def map_method(self, method_name, job):
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


class ResultDispatcher(Dispatcher):

    def __init__(self):
        super(ResultDispatcher, self).__init__('avocado.plugins.result')

    def map_method(self, method_name, result, job):
        for ext in self.extensions:
            try:
                if hasattr(ext.obj, method_name):
                    method = getattr(ext.obj, method_name)
                    method(result, job)
            except SystemExit:
                raise
            except KeyboardInterrupt:
                raise
            except:
                job.log.error('Error running method "%s" of plugin "%s": %s',
                              method_name, ext.name, sys.exc_info()[1])
