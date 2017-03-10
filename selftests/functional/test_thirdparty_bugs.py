import json
import unittest

try:
    from urllib2 import URLError
except ImportError:
    from urllib.error import URLError

from avocado.utils import download


class TestThirdPartyBugs(unittest.TestCase):
    """
    Class created to verify third-party known issues
    """

    def test_paramiko_ecsda_bug(self):
        # https://github.com/paramiko/paramiko/issues/243
        # Problems with using ECDSA known_hosts keys when negotiation also
        # accepts RSA or DSS keys
        try:
            issue_url = 'https://api.github.com/repos/paramiko/paramiko/issues/243'
            issue = json.load(download.url_open(issue_url))
            self.assertEqual(issue['state'], 'open', 'The issue %s is not open '
                             'anymore. Please double check and, if already fixed, '
                             'change the avocado.conf option '
                             '"reject_unknown_hosts" defaults to True.' %
                             'https://github.com/paramiko/paramiko/issues/243')
        except URLError as details:
            raise unittest.SkipTest(details)


if __name__ == '__main__':
    unittest.main()
