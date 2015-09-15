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


import abc


class PluginBase(object):

    """
    Base for all plugins
    """


class CLIRunBase(PluginBase):

    """
    Base plugin interface for command line extensions to the run command

    Plugins that want to add extensions to the run command should use the
    'avocado.plugins.cli.run' namespace.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        super(CLIRunBase, self).__init__()
        self.kwargs = kwargs

    @abc.abstractmethod
    def configure(self, parser):
        """
        Lets the extension add command line options and do early configuration
        """

    @abc.abstractmethod
    def activate(self, args):
        """
        After the command line is parsed, let the extension activate itself
        """

    @abc.abstractmethod
    def before_run(self, args):
        """
        Hook that extensions can use to run code before test job is run
        """

    @abc.abstractmethod
    def after_run(self, args):
        """
        Hook that extensions can use to run code before test job is run
        """


class JobResultBase(PluginBase):

    """
    Keeps track of job results and writes that to a given output

    Concrete implementations can write to their implemented output whenever it
    makes sense. For some, it may make sense to stream the results, for others
    it may be necessary to write the complete results at once.
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        super(JobResultBase, self).__init__()
        self.kwargs = kwargs

    @abc.abstractmethod
    def start(self, output=None):
        """
        Called once before job is executed.

        :param output: path or URI to where the result will be written to
        """

    @abc.abstractmethod
    def start_tests(self, count=0):
        """
        Called once before any test is executed.

        :param count: the predicted number of tests that will be executed
        :type count: int
        """

    @abc.abstractmethod
    def end_tests(self):
        """
        Called once after all tests are executed.
        """

    @abc.abstractmethod
    def end(self):
        """
        Called once before job is completed.
        """

    @abc.abstractmethod
    def update_test(self, **kwargs):
        """
        Called to update the status on a given test
        """
