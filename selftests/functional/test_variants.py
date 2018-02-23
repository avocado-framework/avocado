import os
import tempfile
import shutil
import unittest

from avocado.utils import process


basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
basedir = os.path.abspath(basedir)

AVOCADO = os.environ.get("UNITTEST_AVOCADO_CMD", "./scripts/avocado")


class VariantsDumpLoadTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.variants_file = os.path.join(self.tmpdir, 'variants.json')
        self.content = ('[{"paths": ["/run/*"], '
                        '"variant": [["/", []]], '
                        '"variant_id": null}]')

    def test_variants_dump(self):
        cmd_line = ('%s variants --json-variants-dump %s' %
                    (AVOCADO, self.variants_file))
        process.run(cmd_line)
        with open(self.variants_file, 'r') as file_obj:
            self.assertEqual(file_obj.read(), self.content)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
