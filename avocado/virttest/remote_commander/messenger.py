#!/usr/bin/env python

'''
Created on Dec 6, 2013

:author: jzupka
'''

import os
import logging
import select
import cPickle
import time
import remote_interface
import cStringIO
import base64


class IOWrapper(object):

    """
    Class encaptulates io opearation to be more consist in different
    implementations. (stdio, sockets, etc..)
    """

    def __init__(self, obj):
        """
        :param obj: IO obj for example file decriptor.
        """
        self._obj = obj

    def close(self):
        raise NotImplementedError()

    def read(self, max_len, timeout=None):
        """
        Read function should be reinmplemented as blocking reading from data
        source when timeout is None and nonblocking for timeout is not None.
        Implementation example StdIWrapper.

        :params max_len: Max len of readed data.
        :type max_len: int
        :param timeout: Timeout of reading operation.
        :type timeout: float
        :return: Readed data.
        """
        raise NotImplementedError()

    def write(self, data):
        """
        Write funciton should be implemented for object uded for writing.

        :param data: Data to write.
        :type data: str.
        """
        raise NotImplementedError()

    def fileno(self):
        """
        Function should return file descriptor number. If object should be used
        for standard io operation.

        :return: File number.
        """
        raise NotImplementedError()

    def _wait_for_data(self, max_len, timeout):
        """
        Wait for data for time == timeout.

        :params max_len: Max len of readed data.
        :type max_len: int
        :param timeout: Timeout of reading operation.
        :type timeout: float
        :return: Readed data.
        """
        r, _, _ = select.select([self.fileno()], [], [], timeout)
        if r:
            return self.read(max_len, None)
        return None


class DataWrapper(object):

    """
    Basic implementation of IOWrapper for stdio.
    """

    def decode(self, data):
        """
        Decodes the data which was read.

        :return: decoded data.
        """
        return data

    def encode(self, data):
        """
        Encode data.

        :return: encoded data.
        """
        return data


class DataWrapperBase64(DataWrapper):

    """
    Basic implementation of IOWrapper for stdio.
    """

    def decode(self, data):
        return base64.b64decode(data)

    def encode(self, data):
        return base64.b64encode(data)


class StdIOWrapper(IOWrapper, DataWrapper):

    """
    Basic implementation of IOWrapper for stdio.
    """

    def close(self):
        os.close(self._obj)

    def fileno(self):
        return self._obj


class StdIOWrapperIn(StdIOWrapper):

    """
    Basic implementation of IOWrapper for stdin
    """

    def read(self, max_len, timeout=None):
        if timeout is not None:
            return self._wait_for_data(max_len, timeout)
        else:
            return os.read(self._obj, max_len)


class StdIOWrapperOut(StdIOWrapper):

    """
    Basic implementation of IOWrapper for stdout
    """

    def write(self, data):
        os.write(self._obj, data)


class StdIOWrapperInBase64(StdIOWrapperIn, DataWrapperBase64):

    """
    Basic implementation of IOWrapper for stdin
    """


class StdIOWrapperOutBase64(StdIOWrapperOut, DataWrapperBase64):

    """
    Basic implementation of IOWrapper for stdout
    """


class MessengerError(Exception):

    def __init__(self, msg):
        super(MessengerError, self).__init__(msg)
        self.msg = msg

    def __str__(self):
        return "Messenger ERROR %s" % (self.msg)


def _map_path(mod_name, kls_name):
    if mod_name.endswith('remote_interface'):  # catch all old module names
        mod = remote_interface
        return getattr(mod, kls_name)
    else:
        mod = __import__(mod_name)
        return getattr(mod, kls_name)


class Messenger(object):

    """
    Class could be used for communication between two python process connected
    by communication canal wrapped by IOWrapper class. Pickling is used
    for communication and thus it is possible to communicate every picleable
    object.
    """

    def __init__(self, stdin, stdout):
        """
        :params stdin: Object for read data from communication interface.
        :type stdin: IOWrapper
        :params stdout: Object for write data to communication interface.
        :type stdout: IOWrapper
        """
        self.stdin = stdin
        self.stdout = stdout

        # Unfortunately only static length of data length is supported.
        self.enc_len_length = len(stdout.encode("0" * 10))

    def close(self):
        self.stdin.close()
        self.stdout.close()

    def format_msg(self, data):
        """
        Format message where first 10 char is length of message and rest is
        piclked message.
        """
        pdata = cPickle.dumps(data, cPickle.HIGHEST_PROTOCOL)
        pdata = self.stdout.encode(pdata)
        len_enc = self.stdout.encode("%10d" % len(pdata))
        return "%s%s" % (len_enc, pdata)

    def flush_stdin(self):
        """
        Flush all input data from communication interface.
        """
        const = 16384
        r, _, _ = select.select([self.stdin.fileno()], [], [], 1)
        while r:
            if len(self.stdin.read(const)) < const:
                break
            r, _, _ = select.select([self.stdin.fileno()], [], [], 1)

    def write_msg(self, data):
        """
        Write formated message to communication interface.
        """
        self.stdout.write(self.format_msg(data))

    def _read_until_len(self, timeout=None):
        """
        Deal with terminal interfaces... Read input until gets string
        contains " " and digits len(string) == 10

        :param timeout: timeout of reading.
        """
        data = ""

        endtime = None
        if timeout is not None:
            endtime = time.time() + timeout

        while (len(data) < self.enc_len_length and
               (endtime is None or time.time() < endtime)):
            d = self.stdin.read(1, timeout)
            if d is None:
                return None
            if len(d) == 0:
                return d
            data += d
        if len(data) < self.enc_len_length:
            return None

        return self.stdout.decode(data)

    def read_msg(self, timeout=None):
        """
        Read data from com interface.

        :param timeout: timeout for reading data.
        :type timeout: float
        :return: (True, data) when reading is successful.
                 (False, None) when other side is closed.
                 (None, None) when reading is timeouted.
        """
        data = self._read_until_len(timeout)
        if data is None:
            return (None, None)
        if len(data) == 0:
            return (False, None)
        rdata = None
        try:
            cmd_len = int(data)
            rdata = ""
            rdata_len = 0
            while (rdata_len < cmd_len):
                rdata += self.stdin.read(cmd_len - rdata_len)
                rdata_len = len(rdata)
            rdataIO = cStringIO.StringIO(self.stdin.decode(rdata))
            unp = cPickle.Unpickler(rdataIO)
            unp.find_global = _map_path
            data = unp.load()
        except Exception, e:
            logging.error("ERROR data:%s rdata:%s" % (data, rdata))
            try:
                self.write_msg(remote_interface.MessengerError("Communication "
                                                               "failed.%s" % (e)))
            except OSError:
                pass
            self.flush_stdin()
            raise
        # Debugging commands.
        # if (isinstance(data, remote_interface.BaseCmd)):
        #    print data.func
        return (True, data)
