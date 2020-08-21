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

"""
Operations with strings (conversion and sanitation).

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

#: On import evaluated value representing the system encoding
#: based on system locales using :func:`locale.getpreferredencoding`.
#: Use this value wisely as some files are dumped in different
#: encoding.
ENCODING = locale.getpreferredencoding()

#: String containing all fs-unfriendly chars (Windows-fat/Linux-ext3)
FS_UNSAFE_CHARS = '<>:"/\\|?*;'

# Translate table to replace fs-unfriendly chars
_FS_TRANSLATE = bytes.maketrans(bytes(FS_UNSAFE_CHARS, "ascii"),
                                b'__________')


def bitlist_to_string(data):
    """
    Transform from bit list to ASCII string.

    :param data: Bit list to be transformed
    """
    result = []
    pos = 0
    c = 0
    while pos < len(data):
        c += data[pos] << (7 - (pos % 8))
        if (pos % 8) == 7:
            result.append(c)
            c = 0
        pos += 1
    return ''.join([chr(c) for c in result])


def string_to_bitlist(data):
    """
    Transform from ASCII string to bit list.

    :param data: String to be transformed
    """
    data = [ord(c) for c in data]
    result = []
    for ch in data:
        i = 7
        while i >= 0:
            if ch & (1 << i) != 0:
                result.append(1)
            else:
                result.append(0)
            i -= 1
    return result


def shell_escape(command):
    """
    Escape special characters from a command so that it can be passed
    as a double quoted (" ") string in a (ba)sh command.

    :param command: the command string to escape.

    :return: The escaped command string. The required englobing double
            quotes are NOT added and so should be added at some point by
            the caller.

    See also: http://www.tldp.org/LDP/abs/html/escapingsection.html
    """
    command = command.replace("\\", "\\\\")
    command = command.replace("$", r'\$')
    command = command.replace('"', r'\"')
    command = command.replace('`', r'\`')
    return command


def strip_console_codes(output, custom_codes=None):
    """
    Remove the Linux console escape and control sequences from the console
    output. Make the output readable and can be used for result check. Now
    only remove some basic console codes using during boot up.

    :param output: The output from Linux console
    :type output: string
    :param custom_codes: The codes added to the console codes which is not
                         covered in the default codes
    :type output: string
    :return: the string without any special codes
    :rtype: string
    """
    if "\x1b" not in output:
        return output

    old_word = ""
    return_str = ""
    index = 0
    output = "\x1b[m%s" % output
    console_codes = "%[G@8]|\\[[@A-HJ-MPXa-hl-nqrsu\\`]"
    console_codes += "|\\[[\\d;]+[HJKgqnrm]|#8|\\([B0UK]|\\)"
    if custom_codes is not None and custom_codes not in console_codes:
        console_codes += "|%s" % custom_codes
    while index < len(output):
        tmp_index = 0
        tmp_word = ""
        while (len(re.findall("\x1b", tmp_word)) < 2 and
               index + tmp_index < len(output)):
            tmp_word += output[index + tmp_index]
            tmp_index += 1

        tmp_word = re.sub("\x1b", "", tmp_word)
        index += len(tmp_word) + 1
        if tmp_word == old_word:
            continue
        try:
            special_code = re.findall(console_codes, tmp_word)[0]
        except IndexError:
            if index + tmp_index < len(output):
                raise ValueError("%s is not included in the known console "
                                 "codes list %s" % (tmp_word, console_codes))
            continue
        if special_code == tmp_word:
            continue
        old_word = tmp_word
        return_str += tmp_word[len(special_code):]
    return return_str


def iter_tabular_output(matrix, header=None, strip=False):
    """
    Generator for a pretty, aligned string representation of a nxm matrix.

    This representation can be used to print any tabular data, such as
    database results. It works by scanning the lengths of each element
    in each column, and determining the format string dynamically.

    :param matrix: Matrix representation (list with n rows of m elements).
    :param header: Optional tuple or list with header elements to be displayed.
    :param strip:  Optionally remove trailing whitespace from each row.
    """
    def _get_matrix_with_header():
        return itertools.chain([header], matrix)

    def _get_matrix_no_header():
        return matrix

    if header is None:
        header = []
    if header:
        get_matrix = _get_matrix_with_header
    else:
        get_matrix = _get_matrix_no_header

    lengths = []
    len_matrix = []
    str_matrix = []
    for row in get_matrix():
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
        def str_out(x): return " ".join(x).rstrip()
    else:
        def str_out(x): return " ".join(x)

    for row, row_lens in zip(str_matrix, len_matrix):
        out = []
        padding = [" " * (lengths[i] - row_lens[i])
                   for i in range(len(row_lens))]
        out = ["%s%s" % line for line in zip(row, padding)]
        try:
            out.append(row[-1])
        except IndexError:
            continue    # Skip empty rows
        yield str_out(out)


def tabular_output(matrix, header=None, strip=False):
    """
    Pretty, aligned string representation of a nxm matrix.

    This representation can be used to print any tabular data, such as
    database results. It works by scanning the lengths of each element
    in each column, and determining the format string dynamically.

    :param matrix: Matrix representation (list with n rows of m elements).
    :param header: Optional tuple or list with header elements to be displayed.
    :param strip:  Optionally remove trailing whitespace from each row.
    :return: String with the tabular output, lines separated by unix line feeds.
    :rtype: str
    """
    return "\n".join(iter_tabular_output(matrix, header, strip))


def string_safe_encode(input_str):
    """
    People tend to mix unicode streams with encoded strings. This function
    tries to replace any input with a valid utf-8 encoded ascii stream.

    On Python 3, it's a terrible idea to try to mess with encoding,
    so this function is limited to converting other types into
    strings, such as numeric values that are often the members of a
    matrix.

    :param input_str: possibly unsafe string or other object that can
                      be turned into a string
    :returns: a utf-8 encoded ascii stream
    """
    if not isinstance(input_str, str):
        input_str = str(input_str)
    return input_str


def string_to_safe_path(input_str):
    """
    Convert string to a valid file/dir name.

    This takes a string that may contain characters that are not allowed on
    FAT (Windows) filesystems and/or ext3 (Linux) filesystems, and replaces
    them for safe (boring) underlines.

    It limits the size of the path to be under 255 chars, and make hidden
    paths (starting with ".") non-hidden by making them start with "_".

    :param input_str: String to be converted
    :return: String which is safe to pass as a file/dir name (on recent fs)
    """
    if input_str.startswith("."):
        input_str = "_" + input_str[1:255]
    elif len(input_str) > 255:
        input_str = input_str[:255]

    try:
        return input_str.translate(_FS_TRANSLATE)
    except TypeError:
        # Deal with incorrect encoding
        for bad_chr in FS_UNSAFE_CHARS:
            input_str = input_str.replace(bad_chr, "_")
        return input_str


def is_bytes(data):
    """
    Checks if the data given is a sequence of bytes

    And not a "text" type, that can be of multi-byte characters.
    Also, this does NOT mean a bytearray type.

    :param data: the instance to be checked if it falls under the definition
                 of an array of bytes.
    """
    return isinstance(data, bytes)


def is_text(data):
    """
    Checks if the data given is a suitable for holding text

    That is, if it can hold text that requires more than one byte for
    each character.
    """
    return isinstance(data, str)


def to_text(data, encoding=ENCODING, errors='strict'):
    """
    Convert anything to text decoded text

    When the data is bytes, it's decoded. When it's not of string types
    it's re-formatted into text and returned. Otherwise (it's string)
    it's returned unchanged.

    :param data: data to be transformed into text
    :type data: either bytes or other data that will be returned
                unchanged
    :param encoding: encoding of the data (only used when decoding
                     is necessary)
    :param errors: how to handle encode/decode errors, see:
            https://docs.python.org/3/library/codecs.html#error-handlers
    """
    if is_bytes(data):
        if encoding is None:
            encoding = ENCODING
        return data.decode(encoding, errors=errors)
    elif not isinstance(data, str):
        return str(data)
    return data
