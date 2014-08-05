#!/usr/bin/python

import unittest
import os

import common
import remote
import data_dir


class RemoteFileTest(unittest.TestCase):
    tmp_dir = data_dir.get_tmp_dir()
    test_file_path = os.path.join(tmp_dir, "remote_file")
    default_data = ["RemoteFile Test.\n", "Pattern Line."]

    def __del__(self):
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)

    def _new_remote_file(self):
        if os.path.exists(self.test_file_path):
            os.remove(self.test_file_path)
        test_file = open(self.test_file_path, "w")
        test_file.writelines(self.default_data)
        test_file.close()
        remote_file = remote.RemoteFile(None, "test", None, None, None,
                                        self.test_file_path)
        return remote_file

    def _read_test_file(self):
        test_file = open(self.test_file_path, "r")
        test_data = test_file.readlines()
        test_file.close()
        return test_data

    def testAdd(self):
        remote_file = self._new_remote_file()
        _add_list = ["add_line_1", "add_line_2", "add_line_3"]
        remote_file.add(_add_list)
        test_data = self._read_test_file()
        except_data = ["RemoteFile Test.\n",
                       "Pattern Line.\n",
                       "add_line_1\n",
                       "add_line_2\n",
                       "add_line_3"]
        for index in range(len(except_data)):
            self.assertEqual(except_data[index], test_data[index])
        del remote_file
        test_data = self._read_test_file()
        self.assertEqual(test_data, self.default_data)

    def testSub(self):
        remote_file = self._new_remote_file()
        _pattern2repl = {r"Remote": "Local", r"^Pat.*$": "Replace Line"}
        remote_file.sub(_pattern2repl)
        test_data = self._read_test_file()
        except_data = ["LocalFile Test.\n",
                       "Replace Line"]
        for index in range(len(except_data)):
            self.assertEqual(except_data[index], test_data[index])
        del remote_file
        test_data = self._read_test_file()
        self.assertEqual(test_data, self.default_data)

    def testRemove(self):
        remote_file = self._new_remote_file()
        _pattern_list = [r"^Pattern"]
        remote_file.remove(_pattern_list)
        test_data = self._read_test_file()
        except_data = ["RemoteFile Test."]
        for index in range(len(except_data)):
            self.assertEqual(except_data[index], test_data[index])
        del remote_file
        test_data = self._read_test_file()
        self.assertEqual(test_data, self.default_data)

    def testSEEA(self):
        remote_file = self._new_remote_file()
        _pattern2repl = {r"Remote": "Local", r"NoMatch": "ADD line."}
        remote_file.sub_else_add(_pattern2repl)
        test_data = self._read_test_file()
        except_data = ["LocalFile Test.\n",
                       "Pattern Line.\n",
                       "ADD line."]
        for index in range(len(except_data)):
            self.assertEqual(except_data[index], test_data[index])
        del remote_file
        test_data = self._read_test_file()
        self.assertEqual(test_data, self.default_data)

if __name__ == "__main__":
    unittest.main()
