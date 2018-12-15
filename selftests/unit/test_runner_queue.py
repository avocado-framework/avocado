import argparse
import shutil
import tempfile
import unittest
import multiprocessing
import multiprocessing.queues
import os

from avocado.core.job import Job
from avocado.core.result import Result
from avocado.core.runner import TestRunner
from avocado.core.tree import TreeNode

from .. import setup_avocado_loggers


setup_avocado_loggers()


class TestRunnerQueue(unittest.TestCase):
    """
    Test the Runner/Test Queue
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_" + __name__)
        args = argparse.Namespace(base_logdir=self.tmpdir)
        self.job = Job(args)
        self.result = Result(self.job)

    def _run_test(self, factory):
        """
        Runs a test, specified by the test_factory
        :param factory: the Avocado Test factory
        :return: the last queue message from the test
        """
        if hasattr(multiprocessing, 'SimpleQueue'):
            queue = multiprocessing.SimpleQueue()
        else:
            queue = multiprocessing.queues.SimpleQueue()  # pylint: disable=E1125
        runner = TestRunner(job=self.job, result=self.result)
        runner._run_test(factory, queue)
        while not queue.empty():
            msg = queue.get()
        return msg

    def test_whiteboard(self):
        """
        Tests if the whiteboard content is the expected one
        """
        this = os.path.abspath(__file__)
        base = os.path.dirname(os.path.dirname(os.path.dirname(this)))
        module = os.path.join(base, 'examples', 'tests', 'whiteboard.py')
        factory = ['WhiteBoard',
                   {'methodName': 'test',
                    'tags': set([]),
                    'params': ([TreeNode(name='')], ['/run/*']),
                    'job': self.job,
                    'modulePath': module,
                    'base_logdir': self.tmpdir}]
        msg = self._run_test(factory)

        self.assertEqual(msg['whiteboard'], 'TXkgbWVzc2FnZSBlbmNvZGVkIGluIGJhc2U2NA==\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
