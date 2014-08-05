"""
Base classes supporting Libvirt Sandbox (lxc) container testing

:copyright: 2013 Red Hat Inc.
"""

import logging
import signal
import aexpect


class SandboxException(Exception):

    """
    Basic exception class for problems occurring in SandboxBase or subclasses
    """

    def __init__(self, message):
        super(SandboxException, self).__init__()
        self.message = message

    def __str__(self):
        return self.message


# This is to allow us to alter back-end session management w/o affecting
# sandbox subclasses
class SandboxSession(object):

    """
    Connection instance to asynchronous I/O redirector process
    """

    # Assist with warning on re-use
    used = False

    def __init__(self):
        self.session = None  # createdby new_session

    @property
    def connected(self):
        """
        Represents True/False value if background process was created/opened
        """
        if self.session is None:
            return False
        else:
            return True

    @property
    def session_id(self):
        """
        Returns unique & persistent identifier for the background process
        """
        if self.connected:
            return self.session.get_id()
        else:
            raise SandboxException("Can't get id of non-running sandbox "
                                   "session")

    def new_session(self, command):
        """
        Create and set new opaque session object
        """
        # Allow this to be called more than once w/o consequence
        self.close_session(warn_if_nonexist=self.used)
        self.session = aexpect.Expect(command, auto_close=False)
        self.used = True

    def open_session(self, a_id):
        """
        Restore connection to existing session identified by a_id
        """
        # Allow this to be called more than once w/o consequence
        self.close_session(warn_if_nonexist=self.used)
        aexpect.Expect(a_id=a_id)
        self.used = True

    def close_session(self, warn_if_nonexist=True):
        """
        Finalize assigned opaque session object
        """
        # Allow this to be called more than once w/o consequence
        if self.connected:
            self.session.close()
        else:
            if warn_if_nonexist:
                logging.warning("Closing nonexisting sandbox session")

    def kill_session(self, sig=signal.SIGTERM):
        """
        Send a signal to the opaque session object
        """
        if self.connected:
            self.session.kill(sig=sig)
        else:
            raise SandboxException("Can't send signal to inactive sandbox "
                                   "session")

    def send(self, a_string):
        """Send a_string to session"""
        if self.connected:
            self.session.send(a_string)
        else:
            raise SandboxException("Can't send to an inactive sandbox session")

    def recv(self):
        """Return combined stdout/stderr output received so far"""
        if self.connected:
            return self.session.get_output()
        else:
            raise SandboxException("Can't get output from finalized sandbox "
                                   "session")

    def recvout(self):
        """Return just stdout output"""
        # FIXME: aexpect combines stdout and stderr in a single pipe :(
        raise NotImplementedError

    def recverr(self):
        """Return just stderr output"""
        # FIXME: aexpect combines stdout and stderr in a single pipe :(
        raise NotImplementedError

    def exit_code(self):
        """Block, and return exit code from session"""
        if self.connected:
            return self.session.get_status()
        else:
            raise SandboxException("Can't get exit code from finalized sandbox "
                                   "session")

    def is_running(self):
        """Return True if exit_code() would block"""
        if self.connected:
            return self.session.is_alive()
        else:
            return None

    def auto_clean(self, boolean):
        """Make session cleanup on GC if True"""
        if self.connected:
            self.session.auto_close = boolean
        else:
            raise SandboxException("Can't set auto_clean on disconnected "
                                   "sandbox session")


class SandboxBase(object):

    """
    Base operations for sandboxed command
    """

    # Provide unique instance number for each sandbox
    instances = None

    def __init__(self, params):
        """
        Create a new sandbox interface instance based on this type from params
        """
        # Un-pickling instances doesn't call init again
        if self.__class__.instances is None:
            self.__class__.instances = 1
        else:
            self.__class__.instances += 1
        # store a copy for use to avoid referencing class attribute
        self.identifier = self.__class__.instances
        # Allow global 'lvsb_*' keys to be overridden for specific subclass
        self.params = params.object_params(self.__class__.__name__)
        self.options = None  # opaque value consumed by make_command()
        # Aexpect has some well hidden bugs, private attribute hides
        # interface in case it changes from fixes or gets swapped out
        # entirely.
        self._session = SandboxSession()

    # Allow running sandboxes to persist across multiple tests if needed
    def __getstate__(self):
        """Serialize instance for pickling"""
        # Regular dictionary format for now, but could change later
        state = {'params': self.params,
                 'identifier': self.identifier,
                 'options': self.options}
        # Critical info. to re-connect to session when un-pickle
        if self._session.connected:
            state['session_id'] = self._session.session_id
        return state

    def __setstate__(self, state):
        """Actualize instance from state"""
        for key in ('identifier', 'params', 'options'):
            setattr(self, key, state[key])
        if state.haskey('session_id'):
            self._session = SandboxSession()
            self._session.open_session(state['session_id'])

    def run(self, extra=None):
        """
        Launch new sandbox as asynchronous background sandbox process

        :param extra: String of extra command-line to use but not store
        """
        sandbox_cmdline = self.make_sandbox_command_line(extra)
        logging.debug("Launching %s", sandbox_cmdline)
        self._session.new_session(sandbox_cmdline)

    def stop(self):
        """Destroy but don't finalize asynchronous background sandbox process"""
        self._session.kill_session()

    def fini(self):
        """
        Finalize asynchronous background sandbox process (destroys state!)
        """
        self._session.close_session()

    def send(self, data):
        """Send data to asynchronous background sandbox process"""
        self._session.send(data)

    def recv(self):
        """
        Return stdout and stderr from asynchronous background sandbox process
        """
        return self._session.recv()

    def recvout(self):
        """
        Return only stdout from asynchronous background sandbox process
        """
        return self._session.recvout()

    def recverr(self):
        """
        return only stderr from asynchronous background sandbox process
        """
        return self._session.recverr()

    def running(self):
        """
        Return True/False if asynchronous background sandbox process executing
        """
        return self._session.is_running()

    def exit_code(self):
        """
        Block until asynchronous background sandbox process ends, returning code
        """
        return self._session.exit_code()

    def auto_clean(self, boolean):
        """
        Change behavior of asynchronous background sandbox process on __del__
        """
        self._session.auto_clean(boolean)

    def make_sandbox_command_line(self, extra=None):
        """
        Return the fully formed command-line for the sandbox using self.options
        """
        # These are the abstract methods subclasses must override
        raise NotImplementedError


class SandboxCommandBase(SandboxBase):

    """
    Connection to a single new or existing sandboxed command
    """

    BINARY_PATH_PARAM = 'virt_sandbox_binary'

    # Cache generated name first time it is requested
    _name = None

    def __init__(self, params, name=None):
        """
        Initialize sandbox-command with params and name, autogenerate if None
        """
        if name is not None:
            self._name = name
        super(SandboxCommandBase, self).__init__(params)

    def __getstate__(self):
        """Serialize instance for pickling"""
        state = super(SandboxCommandBase, self).__getstate__()
        state['name'] = self._name
        return state

    def __setstate__(self, state):
        """Actualize instance from state"""
        self._name = state.pop('name')
        super(SandboxCommandBase, self).__setstate__(state)

    def __get_name__(self):
        """
        Represent a unique sandbox name generated from class and identifier
        """
        # Use shortest possible unique names for instances to be easier
        # to track and make name-comparison fast when there are 10000's
        # of sandboxes. Only use upper-case letters from class name along
        # with instance identifier attribute.
        if self._name is None:
            class_name = self.__class__.__name__
            class_initials = class_name.translate(None,
                                                  'abcdefghijklmnopqrstuvwxyz')
            self._name = "%s_%d" % (class_initials, self.identifier)
        return self._name

    @staticmethod
    def __set_name__(value):
        del value  # not used
        raise SandboxException("Name is read-only")

    @staticmethod
    def __del_name__():
        raise SandboxException("Name is read-only")

    name = property(__get_name__, __set_name__, __del_name__)

    @staticmethod
    def flaten_options(options):
        """
        Convert a list of tuples into space-seperated options+argument string
        """
        result_list = []
        for option, argument in options:
            # positional argument
            if option is None:
                if argument is not None:
                    result_list.append(argument)
                # both empty, ignore
            else:  # option is not None
                # --flag
                if argument is None:
                    result_list.append(option)
                else:  # argument is not None
                    # --option argument or -o argument
                    result_list.append("%s %s" % (option, argument))
        if len(result_list) > 0:
            return " " + " ".join(result_list)
        else:  # they were all (None, None)
            return ""

    def make_sandbox_command_line(self, extra=None):
        """Return entire command-line string needed to start sandbox"""
        command = self.params[self.BINARY_PATH_PARAM]  # mandatory param
        if self.options is not None:
            command += self.flaten_options(self.options)
        if extra is not None:
            command += ' ' + extra
        return command

    def add_optarg(self, option, argument):
        """
        Add an option with an argument into the list of command line options
        """
        if self.options is None:
            self.options = []
        self.options.append((option, argument))

    def add_flag(self, option):
        """
        Add a flag into the list of command line options
        """
        # Tuple encoding required for flaten_options()
        self.add_optarg(option, None)

    def add_pos(self, argument):
        """
        Add a positional option into the list of command line options
        """
        # Tuple encoding required for flaten_options()
        self.add_optarg(None, argument)

    def add_mm(self):
        """
        Append a -- to the end of the current option list
        """
        self.add_pos('--')

    def list_long_options(self):
        """
        Return a list of all long options with an argument
        """
        return [opt for opt, arg in self.options
                if opt.startswith('--') and arg is not None]

    def list_short_options(self):
        """
        Return a list of all short options with an argument
        """
        result = []
        for opt, arg in self.options:
            if arg is None:
                continue  # flag or positional
            if len(opt) > 1 and opt[0] == '-' and opt[1] != '-':
                result.append(opt)

    def list_flags(self):
        """
        Return a list of all flags (options without arguments)
        """
        return [opt for opt, arg in self.options
                if opt.startswith('--') and arg is None]

    def list_pos(self):
        """
        Return a list of all positional arguments
        """
        return [arg for opt, arg in self.options if opt is None]


# Instances are similar to a list-of-lists- multiple kinds (classes) of
# multiple sandobx executions.
class TestSandboxes(object):

    """
    Aggregate manager class of SandboxCommandBase or subclass instances
    """

    # The class of each sandbox instance to operate on
    SANDBOX_TYPE = SandboxCommandBase

    def __init__(self, params, env):
        """
        Create instance(s) of sandbox from a command
        """
        # public attribute for access to each sandbox execution
        self.sandboxes = []
        # Each sandbox type will object_params() itself
        self.params = params
        # In case a subclass wants to interface with tests before/after
        self.env = env
        # Parse out aggregate manager class-specific params
        pop = self.params.object_params(self.__class__.__name__)
        # Allows iterating over all sandboxes e.g. with for_each()
        self.count = int(pop.get('lvsb_count', '1'))
        # Simple-case is all sandboxes on the local host
        self.uri = pop.get('lvsb_uri', 'lxc:///')
        # The command to run inside the sandbox
        self.command = pop.get('lvsb_command')
        # Allows iterating for the options
        self.opts_count = int(pop.get('lvsb_opts_count', '1'))
        # FIXME: should automatically generate this
        self.lvsb_option_mapper = {'optarg': {'connect': '-c', 'name': '-n',
                                              'mount': '-m', 'include': '-i',
                                              'includefile': '-I', 'network': '-N',
                                              'security': '-s'},
                                   'flag': {'help': '-h', 'version': '-V',
                                            'debug': '-d', 'privileged': '-p',
                                            'shell': '-l'}}
        # The list to save options
        self.opts = []
        self.flag = []
        for k in self.lvsb_option_mapper.keys():
            # k may be 'optarg' or 'flag'
            for key, value in self.lvsb_option_mapper[k].items():
                base_name = 'lvsb_%s_options' % key
                for key_gen, option in params.object_counts('lvsb_opts_count',
                                                            base_name):
                    # k is 'optarg'
                    if option and value:
                        self.opts.append((value, option))
                    # k is 'flag'
                    if params.has_key(key_gen) and not option:
                        self.flag.append(value)

        logging.debug("All of options(%s) and flags(%s)", self.opts, self.flag)

    def init_sandboxes(self):
        """
        Create self.count Sandbox instances
        """
        # self.sandboxes probably empty, can't use for_each()
        for index in xrange(0, self.count):
            del index  # Keep pylint happy
            self.sandboxes.append(self.SANDBOX_TYPE(self.params))

    def for_each(self, do_something, *args, **dargs):
        """
        Iterate over all sandboxes, calling do_something on each

        :param do_sometihng: Called with the item and ``*args``, ``**dargs``
        """
        # Simplify making the same call to every running sandbox
        return [do_something(sandbox, *args, **dargs)
                for sandbox in self.sandboxes]

    def are_running(self):
        """
        Return the number of sandbox processes still running
        """
        running = 0
        for is_running in self.for_each(lambda sb: sb.running()):
            if is_running:
                running += 1
        return running

    def are_failed(self):
        """
        Return the number of sandbox processes with non-zero exit codes
        """
        # Warning, this will block if self.are_running() > 0
        failed = 0
        for exit_code in self.for_each(lambda sb: sb.exit_code()):
            if exit_code != 0:
                failed += 1
        return failed
