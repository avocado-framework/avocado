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
