"""
Class that describes a sequence of automated operations.
"""

JOB_STATUSES = {"TEST_NA": False,
                "ABORT": False,
                "ERROR": False,
                "FAIL": False,
                "WARN": False,
                "PASS": True,
                "START": True,
                "ALERT": False,
                "RUNNING": False,
                "NOSTATUS": False}


class Job(object):
    pass
