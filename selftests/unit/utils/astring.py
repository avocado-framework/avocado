import sys
import unittest

from avocado.utils import astring, path


class AstringUtilsTest(unittest.TestCase):
    def test_tabular_output(self):

        self.assertEqual(astring.tabular_output([]), "")
        self.assertEqual(
            astring.tabular_output([], header=("C1", "C2", "C3")), "C1 C2 C3"
        )
        self.assertEqual(astring.tabular_output([["v11", "v12", "v13"]]), "v11 v12 v13")
        self.assertEqual(
            astring.tabular_output(
                [["v11", "v12", "v13"], ["v21", "v22", "v23"]],
                header=("C1", "C2", "C3"),
            ),
            "C1  C2  C3" + "\n" + "v11 v12 v13" + "\n" + "v21 v22 v23",
        )
        self.assertEqual(
            astring.tabular_output(
                [["v11", "v12", ""], ["v21", "v22", "v23"]], header=("C1", "C2", "C3")
            ),
            "C1  C2  C3" + "\n" + "v11 v12 " + "\n" + "v21 v22 v23",
        )
        self.assertEqual(
            astring.tabular_output(
                [["v11", "v12", ""], ["v21", "v22", "v23"]],
                header=("C1", "C2", "C3"),
                strip=True,
            ),
            "C1  C2  C3" + "\n" + "v11 v12" + "\n" + "v21 v22 v23",
        )

        self.assertEqual(
            astring.tabular_output(
                [["v11", "v12", ""], ["v2100", "v22", "v23"], ["v31", "v320", "v33"]],
                header=("C1", "C02", "COL3"),
            ),
            "C1    C02  COL3"
            + "\n"
            + "v11   v12  "
            + "\n"
            + "v2100 v22  v23"
            + "\n"
            + "v31   v320 v33",
        )

    def test_tabular_with_console_codes(self):
        matrix = [
            ("a", "an", "dog", "word", "last"),
            (
                "\x1b[94ma",  # {BLUE}a
                "\033[0man",  # {END}an
                "cc\033[91mc",  # cc{RED}c
                # {RED}d{GREEN}d{BLUE}d{GRAY}d{END}
                "\033[91md\033[92md\033[94md\033[90md\033[0m",
                "last",
            ),
        ]
        header = ["0", "1", "2", "3", "4"]
        self.assertEqual(
            astring.tabular_output(matrix, header),
            "0 1  2   3    4\n"
            "a an dog word last\n"
            "\x1b[94ma \x1b[0man cc\x1b[91mc "
            "\x1b[91md\x1b[92md\x1b[94md\x1b[90md\x1b[0m last",
        )

    def test_tabular_output_different_no_cols(self):
        matrix = [[], [1], [2, 2], [333, 333, 333], [4, 4, 4, 4444]]
        self.assertEqual(
            astring.tabular_output(matrix),
            "1\n2   2\n333 333 333\n4   4   4   4444",
        )

    # This could be a skip based on the Python version, but this is more
    # specific to the exact reason why it does/doesn't make sense to run it
    @unittest.skipUnless(
        sys.getdefaultencoding() == "ascii",
        "Test verifies conversion behavior of between ascii and utf-8 only",
    )
    def test_unicode_tabular(self):
        """
        Verifies tabular can handle utf-8 chars properly

        It tries valid encoded utf-8 string as well as unicode ones of
        various lengths and verifies calculates the right length and reports
        the correct results. (the string_safe_encode function is in use here)
        """

        matrix = [
            ("\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4\xff", 123),
            ("\u0430\u0432\u043e\u043a\u0430\u0434\xff", 123),
            ("avok\xc3\xa1do", 123),
            ("a\u0430", 123),
        ]  # pylint: disable=W1402
        str_matrix = (
            "\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4"
            "\xef\xbf\xbd 123\n"
            "\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4"
            "\xc3\xbf 123\n"
            "avok\xc3\xa1do 123\n"
            "a\u0430 123"
        )  # pylint: disable=W1402
        self.assertEqual(astring.tabular_output(matrix), str_matrix)

    def test_safe_path(self):
        self.assertEqual(astring.string_to_safe_path('a<>:"/\\|\\?*b'), "a__________b")
        self.assertEqual(astring.string_to_safe_path(".."), "_.")
        name = " " * 300
        max_length = path.get_max_file_name_length(name)
        self.assertEqual(len(astring.string_to_safe_path(" " * 300)), max_length)
        avocado = "\u0430\u0432\u043e\u043a\u0430\u0434\xff<>"
        self.assertEqual(astring.string_to_safe_path(avocado), f"{avocado[:-2]}__")

    def test_is_bytes(self):
        """
        Verifies what bytes means, basically that they are the same
        thing across Python 2 and 3 and can be decoded into "text"
        """
        binary = b""
        text = ""
        self.assertTrue(astring.is_bytes(binary))
        self.assertFalse(astring.is_bytes(text))
        self.assertTrue(hasattr(binary, "decode"))
        self.assertTrue(astring.is_text(binary.decode()))
        self.assertFalse(astring.is_bytes(""))

    def test_is_text(self):
        """
        Verifies what text means, basically that they can represent
        extended set of characters and can be encoded into "bytes"
        """
        binary = b""
        text = ""
        self.assertTrue(astring.is_text(text))
        self.assertFalse(astring.is_text(binary))
        self.assertTrue(hasattr(text, "encode"))
        self.assertTrue(astring.is_bytes(text.encode()))

    def test_to_text_is_text(self):
        self.assertTrue(astring.is_text(astring.to_text(b"")))
        self.assertTrue(astring.is_text(astring.to_text("")))
        self.assertTrue(astring.is_text(astring.to_text("")))

    def test_to_text_decode_is_text(self):
        self.assertTrue(astring.is_text(astring.to_text(b"", "ascii")))
        self.assertTrue(astring.is_text(astring.to_text("", "ascii")))
        self.assertTrue(astring.is_text(astring.to_text("", "ascii")))

    def test_to_text(self):
        text_1 = astring.to_text(b"\xc3\xa1", "utf-8")
        text_2 = astring.to_text("\u00e1", "utf-8")
        self.assertTrue(astring.is_text(text_1))
        self.assertEqual(text_1, text_2)
        self.assertEqual(astring.to_text(Exception("\u00e1")), "\xe1")
        # For tuple, dict and others astring.to_text is equivalent of str()
        # because on py3 it's unicode and on py2 it uses __repr__ (is encoded)
        self.assertEqual(astring.to_text({"\xe1": 1}), str({"\xe1": 1}))

    def test_bitlist_to_string(self):
        """Test bitlist_to_string function."""
        # Test basic conversion
        bitlist = [0, 1, 0, 0, 0, 0, 0, 1]  # 'A' = 65
        result = astring.bitlist_to_string(bitlist)
        self.assertEqual(result, "A")

        # Test multiple characters
        bitlist = [0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0]  # 'A' = 65, 'B' = 66
        result = astring.bitlist_to_string(bitlist)
        self.assertEqual(result, "AB")

        # Test empty list
        result = astring.bitlist_to_string([])
        self.assertEqual(result, "")

        # Test partial byte (less than 8 bits) - returns empty string
        result = astring.bitlist_to_string([1])
        self.assertEqual(result, "")

        # Test 7 bits (incomplete byte) - returns empty string
        result = astring.bitlist_to_string([1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(result, "")

    def test_string_to_bitlist(self):
        """Test string_to_bitlist function."""
        # Test single character
        result = astring.string_to_bitlist("A")
        expected = [0, 1, 0, 0, 0, 0, 0, 1]  # 'A' = 65
        self.assertEqual(result, expected)

        # Test multiple characters
        result = astring.string_to_bitlist("AB")
        expected = [
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            1,
            0,
            1,
            0,
            0,
            0,
            0,
            1,
            0,
        ]  # 'A' = 65, 'B' = 66
        self.assertEqual(result, expected)

        # Test empty string
        result = astring.string_to_bitlist("")
        self.assertEqual(result, [])

        # Test round trip conversion
        original = "Hello"
        bitlist = astring.string_to_bitlist(original)
        converted_back = astring.bitlist_to_string(bitlist)
        self.assertEqual(original, converted_back)

    def test_shell_escape(self):
        """Test shell_escape function."""
        # Test basic escaping
        self.assertEqual(astring.shell_escape("hello"), "hello")

        # Test backslash escaping
        self.assertEqual(astring.shell_escape("hello\\world"), "hello\\\\world")

        # Test dollar sign escaping
        self.assertEqual(astring.shell_escape("hello$world"), r"hello\$world")

        # Test double quote escaping
        self.assertEqual(astring.shell_escape('hello"world'), r"hello\"world")

        # Test backtick escaping
        self.assertEqual(astring.shell_escape("hello`world"), r"hello\`world")

        # Test multiple special characters
        self.assertEqual(astring.shell_escape('hello\\$"`world'), r"hello\\\$\"\`world")

        # Test empty string
        self.assertEqual(astring.shell_escape(""), "")

    def test_strip_console_codes(self):
        """Test strip_console_codes function."""
        # Test string without console codes
        self.assertEqual(astring.strip_console_codes("hello world"), "hello world")

        # Test basic ANSI color codes
        input_str = "\x1b[31mred text\x1b[0m"
        self.assertEqual(astring.strip_console_codes(input_str), "red text")

        # Test multiple color codes
        input_str = "\x1b[91mred\x1b[92mgreen\x1b[94mblue\x1b[0m"
        self.assertEqual(astring.strip_console_codes(input_str), "redgreenblue")

        # Test with text between codes
        input_str = "\x1b[94mblue\x1b[0m normal \x1b[91mred\x1b[0m"
        self.assertEqual(astring.strip_console_codes(input_str), "blue normal red")

        # Test custom codes (should be in \x1b[...] format)
        input_str = "\x1b[Xcustomcode test"
        self.assertEqual(
            astring.strip_console_codes(input_str, custom_codes="X"), "customcode test"
        )

        # Test empty string
        self.assertEqual(astring.strip_console_codes(""), "")

        # Test string with only console codes
        self.assertEqual(astring.strip_console_codes("\x1b[31m\x1b[0m"), "")

    def test_iter_tabular_output(self):
        """Test iter_tabular_output function."""
        # Test basic functionality
        matrix = [["a", "b"], ["c", "d"]]
        result = list(astring.iter_tabular_output(matrix))
        self.assertEqual(result, ["a b", "c d"])

        # Test with header
        result = list(astring.iter_tabular_output(matrix, header=["H1", "H2"]))
        self.assertEqual(result, ["H1 H2", "a  b", "c  d"])

        # Test with strip=True
        matrix = [["a", "b   "], ["c", "d"]]
        result = list(astring.iter_tabular_output(matrix, strip=True))
        self.assertEqual(result, ["a b", "c d"])

        # Test empty matrix
        result = list(astring.iter_tabular_output([]))
        self.assertEqual(result, [])

        # Test empty matrix with header
        result = list(astring.iter_tabular_output([], header=["H1", "H2"]))
        self.assertEqual(result, ["H1 H2"])

        # Test different column lengths
        matrix = [[], ["a"], ["b", "c"], ["d", "e", "f"]]
        result = list(astring.iter_tabular_output(matrix))
        self.assertEqual(result, ["a", "b c", "d e f"])

    def test_string_safe_encode(self):
        """Test string_safe_encode function."""
        # Test string input
        self.assertEqual(astring.string_safe_encode("hello"), "hello")

        # Test unicode string
        self.assertEqual(astring.string_safe_encode("héllo"), "héllo")

        # Test integer input
        self.assertEqual(astring.string_safe_encode(123), "123")

        # Test float input
        self.assertEqual(astring.string_safe_encode(123.45), "123.45")

        # Test boolean input
        self.assertEqual(astring.string_safe_encode(True), "True")
        self.assertEqual(astring.string_safe_encode(False), "False")

        # Test None input
        self.assertEqual(astring.string_safe_encode(None), "None")

        # Test list input
        self.assertEqual(astring.string_safe_encode([1, 2, 3]), "[1, 2, 3]")

    def test_to_text_edge_cases(self):
        """Test edge cases for to_text function."""
        # Test with different error handling modes
        self.assertEqual(astring.to_text(b"hello", errors="ignore"), "hello")
        self.assertEqual(astring.to_text(b"hello", errors="replace"), "hello")

        # Test with None encoding (should use default)
        self.assertEqual(astring.to_text(b"hello", encoding=None), "hello")

        # Test with numeric types
        self.assertEqual(astring.to_text(42), "42")
        self.assertEqual(astring.to_text(3.14), "3.14")

        # Test with complex object
        self.assertEqual(astring.to_text([1, 2, 3]), "[1, 2, 3]")

    def test_string_to_safe_path_edge_cases(self):
        """Test edge cases for string_to_safe_path function."""
        # Test multiple consecutive unsafe chars
        self.assertEqual(astring.string_to_safe_path("a<<>>b"), "a____b")

        # Test all unsafe characters
        unsafe = '<>:"/\\|?*;'
        expected = "_" * len(unsafe)
        self.assertEqual(astring.string_to_safe_path(unsafe), expected)

        # Test path starting with multiple dots
        self.assertEqual(astring.string_to_safe_path("...test"), "_..test")

        # Test Unicode characters with unsafe chars
        input_str = "тест<>файл"
        result = astring.string_to_safe_path(input_str)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)


if __name__ == "__main__":
    unittest.main()
