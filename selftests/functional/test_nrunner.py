import unittest

from .. import AVOCADO

from avocado.utils import process
from avocado.core import exit_codes


class RunnableRun(unittest.TestCase):

    def test_noop(self):
        res = process.run("%s runnable-run -k noop" % AVOCADO,
                          ignore_status=True)
        self.assertEqual(res.stdout, b"{'status': 'finished'}\n")
        self.assertEqual(res.exit_status, exit_codes.AVOCADO_ALL_OK)
