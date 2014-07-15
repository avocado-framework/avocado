'''
Created on Dec 11, 2013

:author: jzupka
'''
import copy


class MessengerError(Exception):

    """
    Represented error in messanger.
    """

    def __init__(self, msg):
        super(MessengerError, self).__init__(msg)
        self.msg = msg

    def __str__(self):
        return "Messenger ERROR %s" % (self.msg)


class CommanderError(MessengerError):

    """
    Represent error in Commnader
    """

    def __init__(self, msg):
        super(CommanderError, self).__init__(msg)

    def __str__(self):
        return "Commander ERROR %s" % (self.msg)


class CmdTraceBack(Exception):

    """
    Represent back-trace used for error tracing on remote side.
    """

    def __init__(self, msg):
        super(CmdTraceBack, self).__init__(msg)
        self.msg = msg

    def __str__(self):
        return "Cmd ERROR %s" % (self.msg)


class CmdMessage(object):

    """
    Base cmd message class
    """
    __slots__ = ["cmd_id"]

    def __init__(self, cmd_id):
        self.cmd_id = cmd_id

    def __getstate__(self):
        return (self.cmd_id)

    def __setstate__(self, state):
        self.cmd_id = state[0]

    def isCmdMsg(self):
        return self.cmd_id is not None

    def __eq__(self, other):
        return self.cmd_id == other.cmd_id


class StdStream(CmdMessage):

    """
    Represent message string data from remote client
    """
    __slots__ = ["msg"]

    def __init__(self, msg, cmd_id=None):
        super(StdStream, self).__init__(cmd_id)
        self.msg = msg

    def __str__(self):
        return (self.msg)

    def __getstate__(self):
        return (self.cmd_id, self.msg)

    def __setstate__(self, state):
        self.cmd_id = state[0]
        self.msg = state[1]


class StdOut(StdStream):

    """
    Represent message from stdout string data from remote client
    """
    __slots__ = []

    def __init__(self, msg, cmd_id=None):
        super(StdOut, self).__init__(msg, cmd_id)

    def __getstate__(self):
        return (self.cmd_id, self.msg)

    def __setstate__(self, state):
        self.cmd_id = state[0]
        self.msg = state[1]


class StdErr(StdStream):

    """
    Represent message from stderr string data from remote client
    """
    __slots__ = []

    def __init__(self, msg, cmd_id=None):
        super(StdErr, self).__init__(msg, cmd_id)

    def __getstate__(self):
        return (self.cmd_id, self.msg)

    def __setstate__(self, state):
        self.cmd_id = state[0]
        self.msg = state[1]


class BaseCmd(CmdMessage):

    """
    Class used for moveing information about commands between master and slave.
    """
    __slots__ = ["func", "args", "kargs", "results", "_async", "_finished",
                 "nh_stdin", "nh_stdout", "nh_stderr", "cmd_hash"]

    single_cmd_id = 0

    def __init__(self, func_cmd, *args, **kargs):
        self.cmd_id = BaseCmd.single_cmd_id
        BaseCmd.single_cmd_id += 1
        super(BaseCmd, self).__init__(self.cmd_id)

        self.func = func_cmd
        self.args = copy.deepcopy(args)
        self.kargs = copy.deepcopy(kargs)
        self.results = None
        self._async = False
        self._finished = False
        self.nh_stdin = None
        self.nh_stdout = None
        self.nh_stderr = None
        self.cmd_hash = None

    def __getstate__(self):
        return (self.cmd_id, self.func, self.args, self.kargs, self.results,
                self._async, self._finished, self.nh_stdin, self.nh_stdout,
                self.nh_stderr, self.cmd_hash)

    def __setstate__(self, state):
        self.cmd_id = state[0]
        self.func = state[1]
        self.args = state[2]
        self.kargs = state[3]
        self.results = state[4]
        self._async = state[5]
        self._finished = state[6]
        self.nh_stdin = state[7]
        self.nh_stdout = state[8]
        self.nh_stderr = state[9]
        self.cmd_hash = state[10]

    def __str__(self):
        str_args = []
        for a in self.args:  # Format str value in args to "val"
            if type(a) is str:
                str_args.append("\"%s\"" % a)
            else:
                str_args.append(a)

        str_kargs = {}
        for key, val in self.kargs:   # Format str value in kargs to "val"
            if type(val) is str:
                str_kargs[key] = "\"%s\"" % val
            else:
                str_kargs[key] = val

        return ("base_cmd: %s(%s)" % (".".join(self.func),
                                      ", ".join(str_args) +
                                      ",".join(str_kargs.items())))

    def is_async(self):
        """
        :return: True if command is async else False
        """
        return self._async

    def is_finished(self):
        """
        :return: True if command is finished else False
        """
        return self._finished

    def update(self, basecmd):
        """
        Sync local class with class moved over the messanger.

        :param basecmd: basecmd from which should be sync data to this instance
        :type basecmd: BaseCmd
        """
        self.results = basecmd.results
        self._finished = basecmd._finished
        self._async = basecmd._async

    def update_cmd_hash(self, basecmd):
        if basecmd.cmd_hash is not None:
            self.cmd_hash = basecmd.cmd_hash
