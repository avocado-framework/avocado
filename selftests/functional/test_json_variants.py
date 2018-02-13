import json
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
        os.chdir(basedir)

    def test_variants_dump(self):
        content = ('[{"paths": ["/run/*"], '
                   '"variant": [["/", []]], '
                   '"variant_id": null}]')
        cmd_line = ('%s variants --json-variants-dump %s' %
                    (AVOCADO, self.variants_file))
        process.run(cmd_line)
        with open(self.variants_file, 'r') as file_obj:
            self.assertEqual(file_obj.read(), content)

    def test_run_load(self):
        content = ('[{"paths": ["/run/*"],'
                   '  "variant": [["/run/params/foo",'
                   '             [["/run/params/foo", "p2", "foo2"],'
                   '              ["/run/params/foo", "p1", "foo1"]]]], '
                   '  "variant_id": "foo-0ead"}, '
                   ' {"paths": ["/run/*"],'
                   '  "variant": [["/run/params/bar",'
                   '             [["/run/params/bar", "p2", "bar2"],'
                   '              ["/run/params/bar", "p1", "bar1"]]]],'
                   '  "variant_id": "bar-d06d"}]')
        with open(self.variants_file, 'w') as file_obj:
            file_obj.write(content)
        cmd_line = ('%s run passtest.py --json-variants-load %s '
                    '--job-results-dir %s --json -' %
                    (AVOCADO, self.variants_file, self.tmpdir))
        result = process.run(cmd_line)
        json_result = json.loads(result.stdout)
        self.assertEqual(json_result["pass"], 2)
        self.assertEqual(json_result["tests"][0]["id"],
                         "1-passtest.py:PassTest.test;foo-0ead")
        self.assertEqual(json_result["tests"][1]["id"],
                         "2-passtest.py:PassTest.test;bar-d06d")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
