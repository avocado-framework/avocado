# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
# client/profilers
# Authors: Martin J Bligh <mbligh@google.com>, John Admanski <jadmanski@google.com>

"""
Profilers are programs that run on background, that aim to measure some system
aspect, such as CPU usage, IO throughput, memory usage, syscall count, among
others.

This module implements the profiler class, that contains the needed skeleton
for people to implement their own profilers.
"""


class Profiler(object):

    def __init__(self, job):
        self.job = job

    def setup(self, *args, **dargs):
        return

    def start(self, test):
        return

    def stop(self, test):
        return

    def report(self, test):
        return
