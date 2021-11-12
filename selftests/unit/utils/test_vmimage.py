import unittest.mock
from urllib.error import HTTPError

from avocado.utils import vmimage
from selftests.utils import setup_avocado_loggers

setup_avocado_loggers()


class VMImage(unittest.TestCase):

    def test_list_providers(self):
        self.assertIsNotNone(vmimage.list_providers())

    def test_concrete_providers_have_name(self):
        for provider in vmimage.list_providers():
            self.assertTrue(hasattr(provider, 'name'))


class VMImageHtmlParser(unittest.TestCase):
    def setUp(self):
        pattern = '^[0-9]+/$'
        self.parser = vmimage.VMImageHtmlParser(pattern)

    def test_handle_starttag_no_a(self):
        self.parser.feed('<html><head><title>Test</title></head>'
                         '<body><h1>VMImage</h1></body></html>')
        self.assertFalse(self.parser.items)

    def test_handle_starttag_with_a_pattern_not_match(self):
        self.parser.feed('<html><head><title>Test</title></head>'
                         '<body><a href="https://test.com/" /></body></html>')
        self.assertFalse(self.parser.items)

    def test_handle_starttag_with_a_pattern_match(self):
        version = '12'
        self.parser.feed('<html><head><title>Test</title></head>'
                         '<body><a href="%s/" /></body></html>' % version)
        self.assertTrue(self.parser.items)
        self.assertEqual(self.parser.items[0], version)

    def test_handle_starttag_with_a_pattern_match_multiple(self):
        versions = ['12', '13', '14']
        links = ['<a href="%s/" />' % version for version in versions]
        html = ('<html><head><title>Test</title></head>'
                '<body>%s</body></html>' % ''.join(links))
        self.parser.feed(html)
        self.assertTrue(self.parser.items)
        self.assertEqual(len(self.parser.items), len(versions))
        self.assertTrue(all(version in self.parser.items for version in versions))


class ImageProviderBase(unittest.TestCase):
    @staticmethod
    def get_html_with_versions(versions):
        html = '<html><head><title>Test</title></head><body>%s</body></html>'
        return html % ''.join(['<a href="%s/" />' % v for v in versions])

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([10, 11, 12])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 12)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_with_float_versions(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([10.1, 10.3, 10.2])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version=r'[0-9]+\.[0-9]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 10.3)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_with_string_versions(self, urlopen_mock):
        html_fixture = self.get_html_with_versions(['abc', 'abcd', 'abcde'])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version=r'[\w]+', build=None, arch=None)
        self.assertEqual(base_image.get_version(), 'abcde')

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_from_bad_url_open(self, urlopen_mock):
        urlopen_mock.side_effect = HTTPError(None, None, None, None, None)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_version()

        self.assertIn('Cannot open', exc.exception.args[0])

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_version_versions_not_found(self, urlopen_mock):
        html_fixture = self.get_html_with_versions([])
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_version()

        self.assertIn('Version not available at', exc.exception.args[0])

    def test_get_image_url_with_none_url_images_and_image_pattern(self):
        base_image = vmimage.ImageProviderBase(version='[0-9]+', build=None, arch=None)

        with self.assertRaises(vmimage.ImageProviderError) as exc:
            base_image.get_image_url()

        self.assertIn('attributes are required to get image url', exc.exception.args[0])


class DebianImageProvider(unittest.TestCase):

    #: Extract from https://cdimage.debian.org/cdimage/openstack/
    VERSION_LISTING = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /cdimage/openstack</title>
  <link rel="stylesheet" href="/layout/autoindex.css" type="text/css">
<meta name="viewport" content="width=device-width, initial-scale=1"> </head>
 <body>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Debian Official Cloud Images for OpenStack -- Getting Debian  - www.debian.org</title>
<link rel="author" href="mailto:webmaster@debian.org">
<link href="https://www.debian.org/debian.css" rel="stylesheet" type="text/css">
<link href="https://www.debian.org/debian-en.css" rel="stylesheet" type="text/css" media="all">

<div id="header">
    <div id="upperheader">
        <div id="logo">
            <a href="https://www.debian.org/" title="Debian Home"><img src="https://www.debian.org/Pics/openlogo-50.png" alt="Debian" width="50" height="61"></a>
        </div> <!-- end logo -->
        <div id="navbar">
            <p class="hidecss"><a href="#content">Skip Quicknav</a></p>
            <ul>
                <li><a href="https://www.debian.org/intro/about">About Debian</a></li>
                <li><a href="https://www.debian.org/distrib/">Getting Debian</a></li>
                <li><a href="https://www.debian.org/support">Support</a></li>
                <li><a href="https://www.debian.org/devel/">Developers' Corner</a></li>
            </ul>
        </div> <!-- end navbar -->
    </div> <!-- end upperheader -->

    <h1>Debian Official Cloud Images for OpenStack</h1>


    <p>
    These are files containing cloud images of the Debian GNU/Linux
    operating system designed for OpenStack.  The files in this
    directory are specifically for the <code>amd64</code>
    and <code>arm64</code> architectures.
    </p>

    <h2>Will the image work on a cloud platform other than OpenStack?</h2>

    <p>
    If your platform supports the EC2 style metadata server (which is
    contacted by cloud-init), and also supports an HDD image (using either
    raw or qcow2 format), then most likely it will work. Note that it will
    <strong>not</strong> work on Amazon EC2 if you are not using the
    HVM mode.
    </p>

    <h2>Where are the Jessie (Debian 8) images?</h2>

    <p>
    Debian Jessie is no longer supported by the Debian Cloud Team, as
    official security support for it ended in June 2018. We strongly
    recommend that users should move on to use Stretch (Debian 9)
    or Buster (Debian 10) instead, our current supported versions.
    </p>

    <p>
    If you understand the lack of support and still have a strong need
    for a Jessie image, they are still available for download - see
    the "archive" directory.
    </p>

    <h2>Other questions?</h2>

    <p>
    Other questions can be forwarded to the OpenStack packaging
    team: <b>debian-openstack at lists.debian.org</b>.
    </p>

</div>
  <table id="indexlist">
   <tr class="indexhead"><th class="indexcolicon"><img src="/icons2/blank.png" alt="[ICO]"></th><th class="indexcolname"><a href="?C=N;O=D">Name</a></th><th class="indexcollastmod"><a href="?C=M;O=A">Last modified</a></th><th class="indexcolsize"><a href="?C=S;O=A">Size</a></th></tr>
   <tr class="indexbreakrow"><th colspan="4"><hr></th></tr>
   <tr class="even"><td class="indexcolicon"><a href="/cdimage/"><img src="/icons2/go-previous.png" alt="[PARENTDIR]"></a></td><td class="indexcolname"><a href="/cdimage/">Parent Directory</a></td><td class="indexcollastmod">&nbsp;</td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="9.12.0/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="9.12.0/">9.12.0/</a></td><td class="indexcollastmod">2020-02-09 16:03  </td><td class="indexcolsize">  - </td></tr>
   <tr class="even"><td class="indexcolicon"><a href="10.3.0/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="10.3.0/">10.3.0/</a></td><td class="indexcollastmod">2020-02-09 03:02  </td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="archive/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="archive/">archive/</a></td><td class="indexcollastmod">2020-02-09 16:10  </td><td class="indexcolsize">  - </td></tr>
   <tr class="even"><td class="indexcolicon"><a href="current-9/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="current-9/">current-9/</a></td><td class="indexcollastmod">2020-02-09 16:03  </td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="current-10/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="current-10/">current-10/</a></td><td class="indexcollastmod">2020-02-09 03:02  </td><td class="indexcolsize">  - </td></tr>
   <tr class="even"><td class="indexcolicon"><a href="current/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="current/">current/</a></td><td class="indexcollastmod">2020-02-09 03:02  </td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="testing/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="testing/">testing/</a></td><td class="indexcollastmod">2019-07-08 13:30  </td><td class="indexcolsize">  - </td></tr>
   <tr class="indexbreakrow"><th colspan="4"><hr></th></tr>
</table>
<address>Apache/2.4.41 (Unix) Server at cdimage.debian.org Port 443</address>
</body></html>"""

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_versions(self, urlopen_mock):
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        provider = vmimage.DebianImageProvider()
        self.assertEqual(provider.get_versions(), ['9.12.0', '10.3.0'])


class OpenSUSEImageProvider(unittest.TestCase):

    #: extracted from https://download.opensuse.org/pub/opensuse/distribution/leap/
    VERSION_LISTING = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
 <head>
  <title>Index of /pub/opensuse/distribution/leap</title>
  <link rel="stylesheet" href="/theme/download.css" type="text/css" />
<meta charset="utf-8" /> <meta http-equiv="X-UA-Compatible" content="IE=edge" /> <meta name="viewport" content="width=device-width, initial-scale=1" /> <meta name="description" content="The openSUSE Download repositories providing all of the software in the openSUSE distributions and openSUSE Build Service repositories" /> <link rel="shortcut icon" type="image/x-icon" href="https://static.opensuse.org/favicon.ico" /> <link rel="icon" href="https://static.opensuse.org/favicon-32.png" sizes="32x32"> <link rel="icon" href="https://static.opensuse.org/favicon-48.png" sizes="48x48"> <link rel="icon" href="https://static.opensuse.org/favicon-64.png" sizes="64x64"> <link rel="icon" href="https://static.opensuse.org/favicon-96.png" sizes="96x96"> <link rel="icon" href="https://static.opensuse.org/favicon-144.png" sizes="144x144"> <link rel="icon" href="https://static.opensuse.org/favicon-192.png" sizes="192x192"> <link rel="apple-touch-icon" href="https://static.opensuse.org/favicon-144.png" sizes="144x144"> <link rel="apple-touch-icon" href="https://static.opensuse.org/favicon-192.png" sizes="192x192"> <link rel="mask-icon" href="https://static.opensuse.org/mask-icon.svg" color="#73ba25" /> <meta name="mobile-web-app-capable" content="yes" /> <meta name="theme-color" content="#73ba25" /> <meta property="og:site_name" content="openSUSE Download" /> <meta property="og:title" content="openSUSE Download" /> <meta property="og:description" content="The openSUSE Download repositories providing all of the software in the openSUSE distributions and openSUSE Build Service repositories" /> <meta property="og:url" content="http://download.opensuse.org" /> <meta property="og:image" content="https://static.opensuse.org/favicon-192.png" /> <meta name="twitter:card" content="summary" /> <meta name="twitter:title" content="openSUSE Download" /> <meta name="twitter:url" content="http://download.opensuse.org" /> <meta name="twitter:image" content="https://static.opensuse.org/favicon-192.png" /> <script src="/theme/setloc.js"></script> <script defer src="https://static.opensuse.org/chameleon-3.0/dist/js/jquery.slim.js"></script> <script defer src="https://static.opensuse.org/chameleon-3.0/dist/js/bootstrap.bundle.js"></script> <script defer src="https://static.opensuse.org/chameleon-3.0/dist/js/chameleon.js"></script> <link rel="canonical" href="http://download.opensuse.org" /> </head>
 <body>
<nav class="navbar noprint navbar-expand-md">

  <a class="navbar-brand" href="/">
    <img src="https://static.opensuse.org/favicon.svg" class="d-inline-block align-top" alt="openSUSE" title="openSUSE"
      width="30" height="30">
    <span class="navbar-title">Download</span>
  </a>

  <button class="navbar-toggler" type="button" data-toggle="collapse" data-target="#navbar-collapse">
    <svg width="1em" height="1em" viewBox="0 0 16 16" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
      <path fill-rule="evenodd"
        d="M2.5 11.5A.5.5 0 0 1 3 11h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zm0-4A.5.5 0 0 1 3 7h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5zm0-4A.5.5 0 0 1 3 3h10a.5.5 0 0 1 0 1H3a.5.5 0 0 1-.5-.5z">
      </path>
    </svg>
  </button>

  <div class="collapse navbar-collapse" id="navbar-collapse">
    <ul class="nav navbar-nav mr-auto flex-md-shrink-0">




      <li class="nav-item dropdown">
        <a class="nav-link dropdown-toggle" href="#" role="button" data-toggle="dropdown" aria-haspopup="true"
          aria-expanded="false">

          Shortcuts
        </a>
        <div class="dropdown-menu">


          <a class="dropdown-item" href="/debug/"> debug</a>



          <a class="dropdown-item" href="/distribution/"> distribution</a>



          <a class="dropdown-item" href="/factory/"> factory</a>



          <a class="dropdown-item" href="/ports/"> ports</a>



          <a class="dropdown-item" href="/repositories/"> repositories</a>



          <a class="dropdown-item" href="/source/"> source</a>



          <a class="dropdown-item" href="/tumbleweed/"> tumbleweed</a>



          <a class="dropdown-item" href="/update/"> update</a>


        </div>
      </li>




    </ul>


  </div>

  <button class="navbar-toggler megamenu-toggler" type="button" data-toggle="collapse" data-target="#megamenu"
    aria-expanded="true">
    <svg class="bi bi-grid" width="1em" height="1em" viewBox="0 0 16 16" fill="currentColor"
      xmlns="http://www.w3.org/2000/svg">
      <path fill-rule="evenodd"
        d="M1 2.5A1.5 1.5 0 0 1 2.5 1h3A1.5 1.5 0 0 1 7 2.5v3A1.5 1.5 0 0 1 5.5 7h-3A1.5 1.5 0 0 1 1 5.5v-3zM2.5 2a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zm6.5.5A1.5 1.5 0 0 1 10.5 1h3A1.5 1.5 0 0 1 15 2.5v3A1.5 1.5 0 0 1 13.5 7h-3A1.5 1.5 0 0 1 9 5.5v-3zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zM1 10.5A1.5 1.5 0 0 1 2.5 9h3A1.5 1.5 0 0 1 7 10.5v3A1.5 1.5 0 0 1 5.5 15h-3A1.5 1.5 0 0 1 1 13.5v-3zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3zm6.5.5A1.5 1.5 0 0 1 10.5 9h3a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 9 13.5v-3zm1.5-.5a.5.5 0 0 0-.5.5v3a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 .5-.5v-3a.5.5 0 0 0-.5-.5h-3z">
      </path>
    </svg>
  </button>

</nav>

<div id="megamenu" class="megamenu collapse"></div>
<main class="container flex-fill my-4">
    <p class="alert alert-info">If you have a server with some space left, and want to help with making the openSUSE experience better for other users,  <a href="https://en.opensuse.org/openSUSE:Mirror_howto">become a mirror</a>!</p>
    <p class="alert alert-warning">This is the download area of the <a href="https://software.opensuse.org/distributions">openSUSE distributions</a> and the <a href="http://build.opensuse.org/">openSUSE Build Service</a>. If you are searching for a specific package for your distribution, we recommend to use our <a href="https://software.opensuse.org/">Software Portal</a> instead.</p>
    <div id="breadcrumbs">
        <ol class="breadcrumb">
            <li class="breadcrumb-item active">
                <svg height="16" width="16" viewBox="0 0 16 16" fill="currentColor" class="mr-1" xmlns="http://www.w3.org/2000/svg">
                    <path d="M.5 8a.5.5 0 0 1 .5.5V12a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8.5a.5.5 0 0 1 1 0V12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V8.5A.5.5 0 0 1 .5 8z"/>
                    <path d="M5 7.5a.5.5 0 0 1 .707 0L8 9.793 10.293 7.5a.5.5 0 1 1 .707.707l-2.646 2.647a.5.5 0 0 1-.708 0L5 8.207A.5.5 0 0 1 5 7.5z"/>
                    <path d="M8 1a.5.5 0 0 1 .5.5v8a.5.5 0 0 1-1 0v-8A.5.5 0 0 1 8 1z"/>
                </svg>
                Download
            </li>
        </ol>
    </div>
    <script type="text/javascript">setloc();</script>

<table><tr><th><img src="/theme/icons/blank.svg" alt="[ICO]" width="16" height="16" /></th><th><a href="?C=N;O=D">Name</a></th><th><a href="?C=M;O=A">Last modified</a></th><th><a href="?C=S;O=A">Size</a></th><th>Metadata</th></tr><tr><th colspan="5"><hr /></th></tr>
<tr><td valign="top"><a href="/pub/opensuse/distribution/"><img src="/theme/icons/up.svg" alt="[DIR]" width="16" height="16" /></a></td><td><a href="/pub/opensuse/distribution/">Parent Directory</a></td><td>&nbsp;</td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="15.0/"><img src="/theme/icons/folder.svg" alt="[DIR]" width="16" height="16" /></a></td><td><a href="15.0/">15.0/</a></td><td align="right">03-Sep-2018 14:11  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="15.1/"><img src="/theme/icons/folder.svg" alt="[DIR]" width="16" height="16" /></a></td><td><a href="15.1/">15.1/</a></td><td align="right">14-May-2019 12:01  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="15.2/"><img src="/theme/icons/folder.svg" alt="[DIR]" width="16" height="16" /></a></td><td><a href="15.2/">15.2/</a></td><td align="right">08-Feb-2021 14:44  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="15.3/"><img src="/theme/icons/folder.svg" alt="[DIR]" width="16" height="16" /></a></td><td><a href="15.3/">15.3/</a></td><td align="right">28-May-2021 17:53  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="42.3/"><img src="/theme/icons/folder.svg" alt="[DIR]" width="16" height="16" /></a></td><td><a href="42.3/">42.3/</a></td><td align="right">21-Jul-2017 09:22  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><th colspan="5"><hr /></th></tr>
</table>
<script type="text/javascript">settable();</script>
</main>
<footer class="footer">
  <div class="container">
    <div class="d-flex justify-content-between">
      <div class="footer-copyright">
        &copy; 2015-2020 SUSE LLC., openSUSE contributors
      </div>
      <div class="list-inline">

        <a class="list-inline-item" href="https://github.com/openSUSE/mirrorbrain">Source Code</a>

        <a class="list-inline-item" href="https://bugzilla.opensuse.org/">Report Bugs</a>

        <a class="list-inline-item" href="https://en.opensuse.org/Imprint">Imprint</a>

      </div>
    </div>
  </div>
</footer>

</body></html>
"""

    def setUp(self):
        self.suse_available_versions = ['15.0', '15.1', '15.2', '15.3', '42.3']
        self.base_images_url = 'https://download.opensuse.org/pub/opensuse/distribution/leap/15.3/appliances/'

    @staticmethod
    def get_html_with_image_link(image_link):
        return '''
            <a href="openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.packages"></a>
            <a href="%s"></a>
            <a href="openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.qcow2.sha256"></a>
        ''' % image_link

    def test_get_best_version_default(self):
        suse_latest_version = 15.3
        suse_provider = vmimage.OpenSUSEImageProvider(arch='x86_64')
        self.assertEqual(suse_provider.get_best_version(self.suse_available_versions),
                         suse_latest_version)

    def test_get_best_version_leap_4_series(self):
        suse_latest_version = 42.3
        suse_provider = vmimage.OpenSUSEImageProvider(version='4(.)*', arch='x86_64')
        self.assertEqual(suse_provider.get_best_version(self.suse_available_versions),
                         suse_latest_version)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_url(self, urlopen_mock):
        image = 'openSUSE-Leap-15.3-JeOS.x86_64-OpenStack-Cloud.qcow2'
        html_fixture = self.get_html_with_image_link(image)
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        expected_image_url = self.base_images_url + image

        suse_provider = vmimage.OpenSUSEImageProvider(arch='x86_64')
        suse_provider.get_version = unittest.mock.Mock(return_value='15.3')
        self.assertEqual(suse_provider.get_image_url(), expected_image_url)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_url_defining_build(self, urlopen_mock):
        image = 'openSUSE-Leap-15.3-JeOS.x86_64-15.3-OpenStack-Cloud-Build1.111.qcow2'
        html_fixture = self.get_html_with_image_link(image)
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        expected_image_url = self.base_images_url + image

        suse_provider = vmimage.OpenSUSEImageProvider(build='1.111',
                                                      arch='x86_64')
        suse_provider.get_version = unittest.mock.Mock(return_value='15.3')
        self.assertEqual(suse_provider.get_image_url(), expected_image_url)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_versions(self, urlopen_mock):
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        provider = vmimage.OpenSUSEImageProvider()
        self.assertEqual(provider.get_versions(),
                         [15.0, 15.1, 15.2, 15.3, 42.3])


class FedoraImageProvider(unittest.TestCase):

    #: extracted from https://dl.fedoraproject.org/pub/fedora/linux/releases/
    VERSION_LISTING = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /pub/fedora/linux/releases</title>
 </head>
 <body>
<h1>Index of /pub/fedora/linux/releases</h1>
<pre><img src="/icons/blank.gif" alt="Icon "> <a href="?C=N;O=D">Name</a>                    <a href="?C=M;O=A">Last modified</a>      <a href="?C=S;O=A">Size</a>  <a href="?C=D;O=A">Description</a><hr><img src="/icons/back.gif" alt="[PARENTDIR]"> <a href="/pub/fedora/linux/">Parent Directory</a>                             -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="10/">10/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="11/">11/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="12/">12/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="13/">13/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="14/">14/</a>                     2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="15/">15/</a>                     2013-09-05 19:09    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="16/">16/</a>                     2013-09-05 19:20    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="17/">17/</a>                     2013-09-05 19:25    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="18/">18/</a>                     2015-02-24 00:45    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="19/">19/</a>                     2015-02-24 00:57    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="20/">20/</a>                     2015-07-16 17:32    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="21/">21/</a>                     2016-05-17 20:38    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="22/">22/</a>                     2017-09-21 17:00    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="23/">23/</a>                     2017-09-21 17:27    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="24/">24/</a>                     2017-09-22 17:36    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="25/">25/</a>                     2018-07-09 23:26    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="26/">26/</a>                     2018-07-09 23:31    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="27/">27/</a>                     2019-04-01 20:08    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="28/">28/</a>                     2019-09-02 20:37    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="29/">29/</a>                     2018-10-26 17:27    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="30/">30/</a>                     2019-04-26 20:58    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="7/">7/</a>                      2016-05-21 03:28    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="8/">8/</a>                      2016-05-21 02:12    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="9/">9/</a>                      2013-04-25 08:48    -
<img src="/icons/folder.gif" alt="[DIR]"> <a href="test/">test/</a>                   2019-07-16 14:04    -
<hr></pre>
</body></html>"""

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_parameters_match(self, urlopen_mock):
        expected_version = '30'
        expected_arch = 'x86_64'
        expected_build = '1234'
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        provider = vmimage.FedoraImageProvider(expected_version, expected_build,
                                               expected_arch)
        image = "Fedora-Cloud-Base-%s-%s.%s.qcow2" % (expected_version, expected_build,
                                                      expected_arch)
        parameters = provider.get_image_parameters(image)
        self.assertEqual(expected_version, parameters['version'])
        self.assertEqual(expected_build, parameters['build'])
        self.assertEqual(expected_arch, parameters['arch'])

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_parameters_not_match(self, urlopen_mock):
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)

        provider = vmimage.FedoraImageProvider('30', '1234',
                                               'x86_64')
        image = 'openSUSE-Leap-15.0-OpenStack.x86_64-1.1.1-Buildlp111.11.11.qcow2'
        parameters = provider.get_image_parameters(image)
        self.assertIsNone(parameters, "get_image_parameters() finds parameters "
                                      "where there should be none")

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_versions(self, urlopen_mock):
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        provider = vmimage.FedoraImageProvider()
        self.assertEqual(provider.get_versions(),
                         [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
                          23, 24, 25, 26, 27, 28, 29, 30, 7, 8, 9])


if __name__ == '__main__':
    unittest.main()
