"""
Higher order classes and functions for Libvirt Sandbox (lxc) container testing

:copyright: 2013 Red Hat Inc.
"""

import datetime
import time
import logging
import lvsb_base

# This utility function lets test-modules quickly create a list of all
# sandbox aggregate types, themselves containing a list of individual
# sandboxes.


def make_sandboxes(params, env, extra_ns=None):
    """
    Return list of instantiated lvsb_testsandboxes classes from params

    :param params: an undiluted Params instance
    :param env: the current env instance
    :param extra_ns: An extra, optional namespace to search for classes
    """
    namespace = globals()  # stuff in this module
    # For specialized sandbox types, allow their class to be defined
    # inside test module or elsewhere.
    if extra_ns is not None:
        namespace.update(extra_ns)  # copy in additional symbols
    names = namespace.keys()
    # Test may require more than one sandbox agregator class
    pobs = params.objects('lvsb_testsandboxes')  # manditory parameter
    # filter out non-TestSandboxes subclasses
    for name in names:
        try:
            if not issubclass(namespace[name], lvsb_base.TestSandboxes):
                # Working on name list, okay to modify dict
                del namespace[name]
        except TypeError:
            # Symbol wasn't a class, just ignore it
            pass
    # Return a list of instantiated sandbox_testsandboxes's classes
    return [namespace[type_name](params, env) for type_name in pobs]


# TestSandboxes subclasses defined below, or inside other namespaces like
# a test module.  They simply help the test-module iterate over many
# aggregate manager classes and the sandboxes they contain.

class TestBaseSandboxes(lvsb_base.TestSandboxes):

    """
    Simplistic sandbox aggregate manager
    """

    def __init__(self, params, env):
        """
        Initialize to run, all SandboxCommandBase's
        """
        super(TestBaseSandboxes, self).__init__(params, env)
        self.init_sandboxes()  # create instances of SandboxCommandBase
        # Point all of them at the same local uri
        self.for_each(lambda sb: sb.add_optarg('-c', self.uri))
        # The flag doesn't require sandbox name
        if not self.flag:
            # Use each instances name() method to produce name argument
            self.for_each(lambda sb: sb.add_optarg('-n', sb.name))

    def command_suffixes(self):
        """
        Append command after a --
        """
        # Command should follow after a --
        self.for_each(lambda sb: sb.add_mm())
        # Each one gets the same command (that's why it's simple)
        self.for_each(lambda sb: sb.add_pos(self.command))

    def results(self, each_timeout=5):
        """
        Run sandboxe(s), allowing each_timeout to complete, return output list
        """
        # Sandboxes run asynchronously, prevent them from running forever
        start = datetime.datetime.now()
        total_timeout_seconds = each_timeout * self.count
        timeout_at = start + datetime.timedelta(seconds=total_timeout_seconds)
        # No need to write a method just to call the run method
        self.for_each(lambda sb: sb.run())
        while datetime.datetime.now() < timeout_at:
            # Wait until number of running sandboxes is zero
            if bool(self.are_running()):
                time.sleep(0.1)  # Don't busy-wait
                continue
            else:  # none are running
                break
        # Needed for accurate time in logging message below
        end = datetime.datetime.now()
        # Needed for logging message if none exited before timeout
        still_running = self.are_running()
        # Cause all exited sessions to clean up when sb.stop() called
        self.for_each(lambda sb: sb.auto_clean(True))
        # If raise, auto_clean will make sure cleanup happens
        if bool(still_running):
            raise lvsb_base.SandboxException("%d of %d sandboxes are still "
                                             "running after "
                                             "the timeout of %d seconds."
                                             % (still_running,
                                                self.count,
                                                total_timeout_seconds))
        # Kill off all sandboxes, just to be safe
        self.for_each(lambda sb: sb.stop())
        logging.info("%d sandboxe(s) finished in %s", self.count,
                     end - start)
        # Return a list of stdout contents from each
        return self.for_each(lambda sb: sb.recv())


# TestBaseSandboxes subclasses which just runs simple default
# options with the same command.

class TestSimpleSandboxes(TestBaseSandboxes):

    """
    Executes a command with simple options
    """

    def __init__(self, params, env):
        """
        Initialize to run, all SandboxCommandBase's
        """
        super(TestSimpleSandboxes, self).__init__(params, env)
        # Appends command after options
        self.command_suffixes()


# TestBaseSandboxes subclasses which runs complex options and allows
# iterating for the options with the same command.

class TestComplexSandboxes(TestBaseSandboxes):

    """
    Executes a command with complex options
    """

    def __init__(self, params, env):
        super(TestComplexSandboxes, self).__init__(params, env)
        # Appends command options
        if self.opts:
            for k, v in self.opts:
                self.for_each(lambda sb: sb.add_optarg(k, v))
            # Appends command after options
            self.command_suffixes()
        if self.flag:
            for k in self.flag:
                self.for_each(lambda sb: sb.add_flag(k))
            # only '-h' and '-V' flags don't require '--' with command
            if "-h" not in self.flag and "-V" not in self.flag:
                # Appends command after options
                self.command_suffixes()
