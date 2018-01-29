import argparse
import shutil
import tempfile
import unittest

from multiprocessing import queues

from avocado.core.job import Job
from avocado.core.result import Result
from avocado.core.runner import TestRunner
from avocado.core.tree import TreeNode


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
        queue = queues.SimpleQueue()
        runner = TestRunner(job=self.job, result=self.result)
        runner._run_test(factory, queue)
        while not queue.empty():
            msg = queue.get()
        return msg

    def test_whiteboard(self):
        """
        Tests if the whiteboard content is the expected one
        """
        factory = ['WhiteBoard',
                   {'methodName': 'test',
                    'tags': set([]),
                    'params': ([TreeNode(name='')], ['/run/*']),
                    'job': self.job,
                    'modulePath': 'examples/tests/whiteboard.py',
                    'base_logdir': self.tmpdir}]
        msg = self._run_test(factory)

        self.assertEquals(msg['whiteboard'], 'ZGVmYXVsdCB3\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
