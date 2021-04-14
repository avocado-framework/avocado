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
# Copyright: Red Hat Inc. 2019
# Author: Cleber Rosa <crosa@redhat.com>

"""
data drainer

This module provides utility classes for draining data and dispatching
it to different destinations.  This is intended to be used
concurrently with other code, usually test code producing the output
to be drained/processed.  A thread is started and maintained on behalf
of the user.
"""

import abc
import io
import os
import select
import threading


class BaseDrainer(abc.ABC):

    """
    Base drainer, doesn't provide complete functionality to be useful.
    """

    name = 'avocado.utils.datadrainer.BaseDrainer'

    def __init__(self, source, stop_check=None, name=None):
        """
        :param source: where to read data from, this is intentionally
                       abstract
        :param stop_check: callable that should determine if the
                           drainer should quit.  If None is given, it
                           will never stop.
        :type stop_check: function
        :param name: instance name of the drainer, used for describing
                     the name of the thread maintained by this instance
        :type name: str
        """
        self._source = source
        if stop_check is None:
            def stop_check():   # pylint: disable=E0102
                return False
        self._stop_check = stop_check
        if name is not None:
            self.name = name
        # internal state flag, used to stop processing because of a
        # condition that may have happened in between the loop cycles
        self._internal_quit = False

    @staticmethod
    def data_available():
        """
        Checks if source appears to have data to be drained
        """
        return False

    @abc.abstractmethod
    def read(self):
        """
        Abstract method supposed to read from the data source
        """

    @abc.abstractmethod
    def write(self, data):
        """
        Abstract method supposed to write the read data to its destination
        """

    def _loop(self):
        """
        Basic implementation of the thread target

        This loops until either an internal quit flag is set, or when
        the stop_check function evaluates to True.
        """
        while True:
            if self._internal_quit:
                break
            if self.data_available():
                self.write(self.read())
            if self._stop_check():
                break

    def start(self):
        """
        Starts a thread to do the data draining
        """
        self._thread = threading.Thread(target=self._loop,  # pylint: disable=W0201
                                        name=self.name)

        self._thread.daemon = True
        self._thread.start()

    def wait(self):
        """
        Waits on the thread completion
        """
        self._thread.join()


class FDDrainer(BaseDrainer):
    """
    Drainer whose source is a file descriptor

    This drainer uses select to efficiently wait for data to be available on
    a file descriptor.  If the file descriptor is closed, the drainer responds
    by shutting itself down.

    This drainer doesn't provide a write() implementation, and is
    consequently not a complete implementation users can pick and use.
    """

    name = 'avocado.utils.datadrainer.FDDrainer'

    def data_available(self):
        try:
            return select.select([self._source], [], [], 1)[0]
        except OSError as exc:
            if exc.errno == 9:
                return False

    def read(self):
        data = b''
        try:
            data = os.read(self._source, io.DEFAULT_BUFFER_SIZE)
        except OSError as exc:
            if exc.errno == 9:
                self._internal_quit = True
        return data

    def write(self, data):
        # necessary to avoid pylint W0223
        raise NotImplementedError


class BufferFDDrainer(FDDrainer):
    """
    Drains data from a file descriptor and stores it in an internal buffer
    """

    name = 'avocado.utils.datadrainer.BufferFDDrainer'

    def __init__(self, source, stop_check=None, name=None):
        super(BufferFDDrainer, self).__init__(source, stop_check, name)
        self._data = io.BytesIO()

    def write(self, data):
        self._data.write(data)

    @property
    def data(self):
        """
        Returns the buffer data, as bytes
        """
        return self._data.getvalue()


class LineLogger(FDDrainer):

    name = 'avocado.utils.datadrainer.LineLogger'

    def __init__(self, source, stop_check=None, name=None, logger=None):
        super(LineLogger, self).__init__(source, stop_check, name)
        self._logger = logger
        self._buffer = io.BytesIO()

    def write(self, data):
        if b'\n' not in data:
            self._buffer.write(data)
            return
        data = self._buffer.getvalue() + data
        lines = data.split(b'\n')
        if not lines[-1].endswith(b'\n'):
            self._buffer.close()
            self._buffer = io.BytesIO()
            self._buffer.write(lines[-1])
        for line in lines:
            line = line.decode(errors='replace').rstrip('\n')
            if line:
                self._logger.debug(line)
