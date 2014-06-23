#!/usr/bin/env python

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
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>


import unittest
import tempfile
import os
import sys
import shutil
import random

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import crypto
from avocado.utils import archive


class ArchiveTest(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp(prefix='archive_datadir_unittest')
        self.compressdir = tempfile.mkdtemp(dir=self.basedir)
        self.decompressdir = tempfile.mkdtemp(dir=self.basedir)
        self.sys_random = random.SystemRandom()

    def compress_and_check_dir(self, extension):
        hash_map_1 = {}
        for i in xrange(self.sys_random.randint(10, 20)):
            if i % 2 == 0:
                compressdir = tempfile.mkdtemp(dir=self.compressdir)
            else:
                compressdir = self.compressdir
            str_length = self.sys_random.randint(30, 50)
            fd, filename = tempfile.mkstemp(dir=compressdir, text=True)
            os.write(fd, crypto.get_random_string(str_length))
            relative_path = filename.replace(self.compressdir, '')
            hash_map_1[relative_path] = crypto.hash_file(filename)

        archive_filename = self.compressdir + extension
        archive.compress(archive_filename, self.compressdir)
        archive.uncompress(archive_filename, self.decompressdir)

        hash_map_2 = {}
        for root, _, files in os.walk(self.decompressdir):
            for name in files:
                file_path = os.path.join(root, name)
                relative_path = file_path.replace(self.decompressdir, '')
                hash_map_2[relative_path] = crypto.hash_file(file_path)

        self.assertEqual(hash_map_1, hash_map_2)

    def compress_and_check_file(self, extension):
        str_length = self.sys_random.randint(30, 50)
        fd, filename = tempfile.mkstemp(dir=self.basedir, text=True)
        os.write(fd, crypto.get_random_string(str_length))
        original_hash = crypto.hash_file(filename)
        dstfile = filename + extension
        archive_filename = os.path.join(self.basedir, dstfile)
        archive.compress(archive_filename, filename)
        archive.uncompress(archive_filename, self.decompressdir)
        decompress_file = os.path.join(self.decompressdir,
                                       os.path.basename(filename))
        decompress_hash = crypto.hash_file(decompress_file)
        self.assertEqual(original_hash, decompress_hash)

    def test_zip_dir(self):
        self.compress_and_check_dir('.zip')

    def test_zip_file(self):
        self.compress_and_check_file('.zip')

    def test_tar_dir(self):
        self.compress_and_check_dir('.tar')

    def test_tar_file(self):
        self.compress_and_check_file('.tar')

    def test_tgz_dir(self):
        self.compress_and_check_dir('.tar.gz')

    def test_tgz_file(self):
        self.compress_and_check_file('.tar.gz')

    def test_tgz_2_dir(self):
        self.compress_and_check_dir('.tgz')

    def test_tgz_2_file(self):
        self.compress_and_check_file('.tgz')

    def test_tbz2_dir(self):
        self.compress_and_check_dir('.tar.bz2')

    def test_tbz2_file(self):
        self.compress_and_check_file('.tar.bz2')

    def test_tbz2_2_dir(self):
        self.compress_and_check_dir('.tbz2')

    def test_tbz2_2_file(self):
        self.compress_and_check_file('.tbz2')

    def tearDown(self):
        pass
        try:
            shutil.rmtree(self.basedir)
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main()
