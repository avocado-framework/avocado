import json
import os
import tempfile
import shutil
import unittest

from avocado.utils import process

from .. import AVOCADO, BASEDIR


class VariantsDumpLoadTests(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.variants_file = os.path.join(self.tmpdir, 'variants.json')
        os.chdir(BASEDIR)

    def test_variants_dump(self):
        cmd_line = ('%s variants --json-variants-dump %s' %
                    (AVOCADO, self.variants_file))
        process.run(cmd_line)
        with open(self.variants_file, 'r') as file_obj:
            file_content = file_obj.read()
            self.assertEqual(file_content[0:2], '[{')
            self.assertIn('"paths": ["/run/*"]', file_content)
            self.assertIn('"variant": [["/", []]]', file_content)
            self.assertIn('"variant_id": null', file_content)
            self.assertEqual(file_content[-2:], '}]')

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
        json_result = json.loads(result.stdout_text)
        self.assertEqual(json_result["pass"], 2)
        self.assertEqual(json_result["tests"][0]["id"],
                         "1-passtest.py:PassTest.test;foo-0ead")
        self.assertEqual(json_result["tests"][1]["id"],
                         "2-passtest.py:PassTest.test;bar-d06d")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
