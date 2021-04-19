import json
import os
import unittest

from avocado.utils import process
from selftests.utils import AVOCADO, TestCaseTmpDir


class VariantsDumpLoadTests(TestCaseTmpDir):

    def setUp(self):
        super(VariantsDumpLoadTests, self).setUp()
        self.variants_file = os.path.join(self.tmpdir.name, 'variants.json')

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
                    (AVOCADO, self.variants_file, self.tmpdir.name))
        result = process.run(cmd_line)
        json_result = json.loads(result.stdout_text)
        self.assertEqual(json_result["pass"], 2)
        self.assertEqual(json_result["tests"][0]["id"],
                         "1-passtest.py:PassTest.test;foo-0ead")
        self.assertEqual(json_result["tests"][1]["id"],
                         "2-passtest.py:PassTest.test;bar-d06d")


if __name__ == '__main__':
    unittest.main()
