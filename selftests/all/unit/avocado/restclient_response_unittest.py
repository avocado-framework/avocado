import os
import sys
import unittest

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.core.restclient import response


class ResultResponseTest(unittest.TestCase):

    GOOD_DATA = ('{"count": 1, "next": null, "previous": null, '
                 '"results": [ { "name": "unknown" } ] }')

    BAD_DATA_JSON = '{"count": 1'

    BAD_DATA_COUNT = ('{"counter": 1, "next": null, "previous": null, '
                      '"results": [ { "name": "unknown" } ] }')

    BAD_DATA_NEXT = ('{"count": 1, "NEXT": null, "previous": null, '
                     '"results": [ { "name": "unknown" } ] }')

    BAD_DATA_PREVIOUS = ('{"count": 1, "next": null, "prev": null, '
                         '"results": [ { "name": "unknown" } ] }')

    BAD_DATA_RESULTS = '{"count": 1, "next": null, "prev": null}'

    def test_good_data(self):
        r = response.ResultResponse(self.GOOD_DATA)
        self.assertEquals(r.count, 1)

    def test_bad_data_json(self):
        self.assertRaises(response.InvalidJSONError,
                          response.ResultResponse,
                          self.BAD_DATA_JSON)

    def test_bad_data_empty(self):
        self.assertRaises(response.InvalidJSONError,
                          response.ResultResponse, '')

    def test_bad_data_count(self):
        self.assertRaises(response.InvalidResultResponseError,
                          response.ResultResponse,
                          self.BAD_DATA_COUNT)

    def test_bad_data_next(self):
        self.assertRaises(response.InvalidResultResponseError,
                          response.ResultResponse,
                          self.BAD_DATA_NEXT)

    def test_bad_data_previous(self):
        self.assertRaises(response.InvalidResultResponseError,
                          response.ResultResponse,
                          self.BAD_DATA_PREVIOUS)

    def test_bad_data_results(self):
        self.assertRaises(response.InvalidResultResponseError,
                          response.ResultResponse,
                          self.BAD_DATA_RESULTS)

if __name__ == '__main__':
    unittest.main()
