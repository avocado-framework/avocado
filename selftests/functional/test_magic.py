from unittest import TestCase

from avocado.core import exit_codes, magic
from avocado.utils import process


class Magic(TestCase):

    def test(self):
        result = process.run('avocado magic', ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK,
                         'Error running "avocado magic"')
        self.assertEqual(result.stdout_text.rstrip(), magic.MAGIC,
                         'Magic numbers mismatch')
