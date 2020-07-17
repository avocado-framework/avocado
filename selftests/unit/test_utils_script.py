import os
import unittest

from avocado.utils import script


class TestTemporary(unittest.TestCase):

    def test_unicode_name(self):
        path = u'\u00e1 \u00e9 \u00ed \u00f3 \u00fa'
        content = "a e i o u"
        with script.TemporaryScript(path, content) as temp_script:
            self.assertTrue(os.path.exists(temp_script.path))
            with open(temp_script.path) as temp_script_file:
                self.assertEqual(content, temp_script_file.read())


if __name__ == "__main__":
    unittest.main()
