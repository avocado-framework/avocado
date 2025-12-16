# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Authors: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""Operations with strings (conversion and sanitation).

The unusual name aims to avoid causing name clashes with the stdlib module
string. Even with the dot notation, people may try to do things like

   import string
   ...
   from avocado.utils import string

And not notice until their code starts failing.
"""

import itertools
import locale
import re

from avocado.utils import path

#: On import evaluated value representing the system encoding
#: based on system locales using :func:`locale.getpreferredencoding`.
#: Use this value wisely as some files are dumped in different
#: encoding.
ENCODING = locale.getpreferredencoding()

#: String containing all fs-unfriendly chars (Windows-fat/Linux-ext3)
FS_UNSAFE_CHARS = '<>:"/\\|?*;'

# Translate table to replace fs-unfriendly chars
_FS_TRANSLATE = bytes.maketrans(bytes(FS_UNSAFE_CHARS, "ascii"), b"__________")


def bitlist_to_string(data):
    """Transform from bit list to ASCII string.

    Converts a list of bits to an ASCII string representation.
    Only complete bytes (8 bits) are processed; partial bytes are ignored.

    :param data: List of integers representing bits to be transformed
    :type data: list[int]
    :returns: ASCII string representation of the bit list
    :rtype: str
    :raises UnicodeDecodeError: If the resulting byte values are not valid ASCII

    .. note::
       Only processes complete bytes. If the bit list length is not a
       multiple of 8, the remaining bits are ignored.

    .. rubric:: Example

    >>> bitlist_to_string([0, 1, 0, 0, 0, 0, 0, 1])  # 'A' = 65
    'A'
    >>> bitlist_to_string([1, 0, 0, 0])  # Incomplete byte
    ''
    """
    result = bytearray()
    c = 0
    for pos, bit in enumerate(data):
        c |= bit << (7 - (pos % 8))
        if (pos % 8) == 7:
            result.append(c)
            c = 0
    return result.decode("ascii")


def string_to_bitlist(data):
    """Transform from ASCII string to bit list.

    Converts each character in the string to its 8-bit binary representation
    and returns a flat list of all bits.

    :param data: ASCII string to be transformed to bit list
    :type data: str
    :returns: List of integers representing the bits of each character
    :rtype: list[int]

    .. note::
       Each character produces exactly 8 bits, with the most significant bit first.

    .. rubric:: Example

    >>> string_to_bitlist('A')  # 'A' = 65 = 01000001
    [0, 1, 0, 0, 0, 0, 0, 1]
    >>> string_to_bitlist('AB')
    [0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0]
    """
    ord_ = ord
    result = []
    append = result.append
    for ch in data:
        ascii_value = ord_(ch)
        for i in range(7, -1, -1):
            append((ascii_value >> i) & 1)
    return result


def shell_escape(command):
    """Escape special characters from a command so that it can be passed
    as a double quoted (" ") string in a (ba)sh command.

    Escapes backslashes, dollar signs, double quotes, and backticks that
    have special meaning in bash when inside double quotes.

    :param command: The command string to escape
    :type command: str
    :returns: The escaped command string safe for shell execution
    :rtype: str
    """
    escape_chars = {"\\": "\\\\", "$": r"\$", '"': r"\"", "`": r"\`"}
    for char, escaped_char in escape_chars.items():
        command = command.replace(char, escaped_char)
    return command


def strip_console_codes(output, custom_codes=None):
    """Remove Linux console escape and control sequences from console output.

    Removes ANSI escape sequences and other console control codes to make
    the output readable and suitable for result checking. Handles common
    codes used during system boot and terminal color formatting.

    :param output: The console output string containing escape sequences
    :type output: str
    :param custom_codes: Additional regex patterns for codes not covered
                        by the default patterns. Will be added to the
                        built-in console codes regex.
    :type custom_codes: str or None
    :returns: Clean string with all console escape sequences removed
    :rtype: str
    :raises ValueError: If unknown console codes are encountered that don't
                       match the known patterns

    .. note::
       If the output doesn't contain ``\\x1b`` (ESC character), the original
       string is returned unchanged for performance.

    .. rubric:: Supported Console Codes

    * ANSI color codes: ``\\x1b[31m``, ``\\x1b[0m``, etc.
    * Cursor positioning: ``\\x1b[H``, ``\\x1b[2J``, etc.
    * Character set selection: ``\\x1b(B``, ``\\x1b(0``, etc.
    * Custom codes via the ``custom_codes`` parameter

    .. rubric:: Example

    >>> strip_console_codes('\\x1b[31mRed Text\\x1b[0m')
    'Red Text'
    >>> strip_console_codes('Normal text')
    'Normal text'
    """
    if "\x1b" not in output:
        return output

    old_word = ""
    return_str = ""
    index = 0
    output = f"\x1b[m{output}"
    console_codes = "%[G@8]|\\[[@A-HJ-MPXa-hl-nqrsu\\`]"
    console_codes += "|\\[[\\d;]+[HJKgqnrm]|#8|\\([B0UK]|\\)"
    if custom_codes is not None and custom_codes not in console_codes:
        console_codes += f"|{custom_codes}"
    while index < len(output):
        tmp_index = 0
        tmp_word = ""
        while len(re.findall("\x1b", tmp_word)) < 2 and index + tmp_index < len(output):
            tmp_word += output[index + tmp_index]
            tmp_index += 1

        tmp_word = re.sub("\x1b", "", tmp_word)
        index += len(tmp_word) + 1
        if tmp_word == old_word:
            continue
        try:
            special_code = re.findall(console_codes, tmp_word)[0]
        except IndexError as exc:
            if index + tmp_index < len(output):
                raise ValueError(
                    f"{tmp_word} is not included in the known "
                    f"console codes list {console_codes}"
                ) from exc
            continue
        if special_code == tmp_word:
            continue
        old_word = tmp_word
        return_str += tmp_word[len(special_code) :]
    return return_str


def iter_tabular_output(matrix, header=None, strip=False):
    """Generator for a pretty, aligned string representation of a nxm matrix.

    This representation can be used to print any tabular data, such as
    database results. It works by scanning the lengths of each element
    in each column, and determining the format string dynamically.

    :param matrix: Matrix representation (list with n rows of m elements).
    :type matrix: list
    :param header: Optional tuple or list with header elements to be displayed.
    :type header: tuple or list or None
    :param strip:  Optionally remove trailing whitespace from each row.
    :type strip: bool
    :returns: Generator yielding each formatted row of the tabular output
    :rtype: generator of str
    """

    lengths = []
    len_matrix = []
    str_matrix = []
    if header:
        matrix = itertools.chain([header], matrix)
    for row in matrix:
        len_matrix.append([])
        str_matrix.append([string_safe_encode(column) for column in row])
        for i, column in enumerate(str_matrix[-1]):
            col_len = len(strip_console_codes(column))
            len_matrix[-1].append(col_len)
            try:
                max_len = lengths[i]
                if col_len > max_len:
                    lengths[i] = col_len
            except IndexError:
                lengths.append(col_len)
        # For different no cols we need to calculate `lengths` of the last item
        # but later in `yield` we don't want it in `len_matrix`
        len_matrix[-1] = len_matrix[-1][:-1]

    if strip:

        def str_out(x):
            """Join list elements and strip trailing whitespace.

            :param x: List of string elements to join
            :type x: list
            :returns: Joined string with trailing whitespace removed
            :rtype: str
            """
            return " ".join(x).rstrip()

    else:

        def str_out(x):
            """Join list elements with spaces.

            :param x: List of string elements to join
            :type x: list
            :returns: Space-separated string of elements
            :rtype: str
            """
            return " ".join(x)

    for row, row_lens in zip(str_matrix, len_matrix):
        out = []
        padding = [" " * (lengths[i] - row_lens[i]) for i in range(len(row_lens))]
        out = ["%s%s" % line for line in zip(row, padding)]  # pylint: disable=C0209
        try:
            out.append(row[-1])
        except IndexError:
            continue  # Skip empty rows
        yield str_out(out)


def tabular_output(matrix, header=None, strip=False):
    """Pretty, aligned string representation of a matrix.

    Creates a single formatted string with column-aligned tabular data,
    suitable for printing or logging. This is a convenience wrapper around
    :func:`iter_tabular_output` that joins all rows with newlines.

    :param matrix: Matrix representation as list of rows, where each row
                  is a list of column elements. Rows may have different lengths.
    :type matrix: list[list]
    :param header: Optional header row elements to be displayed at the top.
                  If provided, will be formatted with the same column alignment.
    :type header: list or tuple or None
    :param strip: If True, removes trailing whitespace from each output row
    :type strip: bool
    :returns: Complete formatted table as a single string with newline separators
    :rtype: str

    .. rubric:: Example

    >>> matrix = [['Alice', '25', 'Engineer'], ['Bob', '30', 'Designer']]
    >>> print(tabular_output(matrix, header=['Name', 'Age', 'Role']))
    Name  Age Role
    Alice 25  Engineer
    Bob   30  Designer

    .. seealso::
       :func:`iter_tabular_output` for the underlying generator implementation
    """
    return "\n".join(iter_tabular_output(matrix, header, strip))


def string_safe_encode(input_str):
    """Safely convert any input to a string representation.

    Handles mixed unicode and encoded strings by ensuring all input
    is converted to a proper string type. In Python 3, this primarily
    serves to convert non-string types (numbers, objects) to strings.

    :param input_str: Input value that needs to be converted to string.
                     Can be string, numeric, or any object with __str__.
    :type input_str: Any
    :returns: String representation of the input
    :rtype: str

    .. note::
       On Python 3, encoding/decoding is handled automatically by the
       language, so this function focuses on type conversion rather than
       encoding management.

    .. rubric:: Supported Input Types

    * Strings: returned as-is
    * Numbers: converted using ``str()``
    * Objects: converted using their ``__str__`` method
    * None: converted to ``'None'``

    .. rubric:: Example

    >>> string_safe_encode('hello')
    'hello'
    >>> string_safe_encode(42)
    '42'
    >>> string_safe_encode([1, 2, 3])
    '[1, 2, 3]'
    """
    if not isinstance(input_str, str):
        input_str = str(input_str)
    return input_str


def string_to_safe_path(input_str):
    """Convert string to a filesystem-safe filename or directory name.

    Sanitizes strings for use as filenames by replacing characters that are
    not allowed on common filesystems (FAT, NTFS, ext3/4) with underscores.
    Also handles length limits and hidden file conventions.

    :param input_str: String to be converted to a safe filename
    :type input_str: str
    :returns: Filesystem-safe string suitable for use as filename or directory name
    :rtype: str

    .. rubric:: Transformations Applied

    * Replaces unsafe characters with underscores: ``< > : " / \\ | ? * ;``
    * Limits length to filesystem maximum (typically 255 characters)
    * Converts hidden files (starting with ``.``) to start with ``_``
    * Handles Unicode characters that may cause encoding issues

    .. rubric:: Cross-Platform Compatibility

    The function ensures compatibility with:

    * **Windows**: FAT32, NTFS filesystems
    * **Linux**: ext3, ext4 filesystems
    * **macOS**: HFS+, APFS filesystems

    .. rubric:: Example

    >>> string_to_safe_path('my file: <test>.txt')
    'my file_ _test_.txt'
    >>> string_to_safe_path('.hidden_file')
    '_hidden_file'
    >>> string_to_safe_path('very_long_filename' * 20)  # Too long
    'very_long_filename...'  # Truncated to max length

    .. seealso::
       :data:`FS_UNSAFE_CHARS` for the complete list of replaced characters
    """
    max_length = path.get_max_file_name_length(input_str)

    if input_str.startswith("."):
        input_str = "_" + input_str[1:max_length]
    elif len(input_str) > max_length:
        input_str = input_str[:max_length]

    try:
        return input_str.translate(_FS_TRANSLATE)
    except TypeError:
        # Deal with incorrect encoding
        for bad_chr in FS_UNSAFE_CHARS:
            input_str = input_str.replace(bad_chr, "_")
        return input_str


def is_bytes(data):
    """Check if the given data is a bytes object.

    Determines whether the input is specifically a ``bytes`` type,
    as opposed to a text string or other sequence type. This is useful
    for encoding/decoding operations and type-specific processing.

    :param data: The data instance to check
    :type data: Any
    :returns: True if data is a bytes object, False otherwise
    :rtype: bool

    .. note::
       This function specifically checks for the ``bytes`` type, not
       ``bytearray`` or other byte-like sequences.

    .. rubric:: Example

    >>> is_bytes(b'hello')
    True
    >>> is_bytes('hello')
    False
    >>> is_bytes(bytearray(b'hello'))
    False
    """
    return isinstance(data, bytes)


def is_text(data):
    """Check if the given data is a text string.

    Determines whether the input is a string type capable of holding
    Unicode text with multi-byte characters, as opposed to a bytes
    sequence or other data type.

    :param data: The data instance to check
    :type data: Any
    :returns: True if data is a text string, False otherwise
    :rtype: bool

    .. note::
       In Python 3, this checks for the ``str`` type, which is Unicode-capable.

    .. rubric:: Example

    >>> is_text('hello')
    True
    >>> is_text(b'hello')
    False
    >>> is_text(42)
    False
    """
    return isinstance(data, str)


def to_text(data, encoding=ENCODING, errors="strict"):
    """Convert any input to a text string.

    Universal text conversion function that handles bytes, strings, and
    other object types. Ensures consistent text output regardless of
    input type while preserving encoding semantics.

    :param data: Data to be converted to text string
    :type data: bytes or str or Any
    :param encoding: Character encoding to use when decoding bytes.
                    Uses system default if None.
    :type encoding: str or None
    :param errors: Error handling scheme for decoding failures.
                  See Python's codec error handlers.
    :type errors: str
    :returns: Text representation of the input data
    :rtype: str
    :raises UnicodeDecodeError: When bytes cannot be decoded with the
                               specified encoding and errors='strict'

    .. rubric:: Conversion Logic

    1. **bytes input**: Decoded using specified encoding
    2. **str input**: Returned unchanged
    3. **Other types**: Converted using ``str()`` function

    .. rubric:: Error Handling Options

    * ``'strict'``: Raise exception on decode errors (default)
    * ``'ignore'``: Skip invalid characters
    * ``'replace'``: Replace invalid characters with ``\\ufffd``
    * ``'backslashreplace'``: Replace with backslash escape sequences

    .. rubric:: Example

    >>> to_text(b'hello', 'utf-8')
    'hello'
    >>> to_text('already text')
    'already text'
    >>> to_text(42)
    '42'
    >>> to_text(b'\xff', 'utf-8', errors='ignore')
    ''

    .. seealso::
       `Python Codec Error Handlers
       <https://docs.python.org/3/library/codecs.html#error-handlers>`_
    """
    if is_bytes(data):
        if encoding is None:
            encoding = ENCODING
        return data.decode(encoding, errors=errors)
    if not isinstance(data, str):
        return str(data)
    return data


# pylint: disable=wrong-import-position
from avocado.utils.deprecation import log_deprecation

log_deprecation.warning("astring")
