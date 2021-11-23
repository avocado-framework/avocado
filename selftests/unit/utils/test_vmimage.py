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

    #: Extract from http://cloud.debian.org/images/cloud/
    VERSION_LISTING = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /images/cloud</title>
  <link rel="stylesheet" href="/layout/autoindex.css" type="text/css">
<meta name="viewport" content="width=device-width, initial-scale=1"> </head>
 <body>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Debian Official Cloud Images -- Getting Debian  - www.debian.org</title>
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
  <h1>Debian Official Cloud Images</h1>

  <p>
    In this page you can find the Debian cloud images provided by the Debian Cloud Team for some cloud providers.
    End users do not need to download these images, as they are
    usually provided by their cloud providers.
    For now we are supporting:

    <ul>
      <li><i>Amazon EC2 (amd64, arm64; Also see <a href="https://wiki.debian.org/Cloud/AmazonEC2Image">the wiki</a> and the <a href="https://aws.amazon.com/marketplace/seller-profile?id=4d4d4e5f-c474-49f2-8b18-94de9d43e2c0&ref=dtl_B0859NK4HC">AWS Marketplace listing</a></i>)</li>
      <li><i>Microsoft Azure (amd64; Also see <a href="https://wiki.debian.org/Cloud/MicrosoftAzure">the wiki</a> and <a href="https://azuremarketplace.microsoft.com/en-us/marketplace/apps?search=debian&page=1">The Azure Marketplace</a></i>)</li>
      <li><i>OpenStack (amd64, arm64, ppc64el; two
      flavours <a href="https://cloud.debian.org/cdimage/cloud/OpenStack/">using
      openstack-debian-images</a> and using the <a href="https://cloud.debian.org/cdimage/cloud/bullseye">toolchain</a> from the
      cloud team.
      Also see <a href="https://wiki.debian.org/OpenStack">the wiki</a></i>)</li>
      <li><i>Plain VM (amd64)</i>, suitable for use with QEMU</li>
    </ul>


    From buster on we provide images for different cloud providers in
    one directory. There we use file names like this:

    <ul>
      <li><tt>debian-11-generic-ppc64el-daily-20210425-618.qcow2</tt></li>
      <li><tt>debian-11-genericcloud-amd64-daily-20210425-618.qcow2</tt></li>
      <li><tt>debian-11-ec2-arm64-daily-20210425-618.tar.xz</tt></li>
    </ul>

    <ul>
  <li><i>azure</i>: Optimized for the Microsoft Azure environment</li>
  <li><i>ec2</i>: Optimized for the Amazon EC2</li>
  <li><i>generic</i>: Should run in any environment using cloud-init,
  for e.g. OpenStack, DigitalOcean and also on bare metal.</li>
  <li><i>genericcloud</i>: Similar to generic. Should run in any
  virtualised environment. Is smaller than `generic` by excluding
  drivers for physical hardware.</li>
  <li><i>nocloud</i>: Mostly useful for testing the build process
   itself. Doesn't have cloud-init installed, but instead allows root
   login without a password. </li>
   </ul>

  </p>

  <h2>How to upload to OpenStack?</h2>

  <p>Once you have downloaded the image, you would typically need to upload it to
  Glance, using a command like this one (example for amd64):</p>

  <pre>openstack image create \
    --container-format bare \
    --disk-format qcow2 \
    --property hw_disk_bus=scsi \
    --property hw_scsi_model=virtio-scsi \
    --property os_type=linux \
    --property os_distro=debian \
    --property os_admin_user=debian \
    --property os_version='10.9.1' \
    --public \
    --file debian-10-generic-arm64-20210329-591.qcow2 \
    debian-10-generic-arm64-20210329-591.qcow2</pre>

  <p>Note that <i>hw_disk_bus=scsi</i> and <i>hw_scsi_model=virtio-scsi</i>
  select the virtio-scsi driver instead of the virtio-blk, which is nicer
  (on older versions of Qemu, virtio-blk doesn't have the FSTRIM feature,
  for example). Also, the properties <i>os_type, os_distro, os_version and
  os_admin_user</i> are OpenStack standards as per
  <a href="https://docs.openstack.org/glance/latest/admin/useful-image-properties.html">this
  document</a>. It is best practice to set them, especialy on public clouds,
  to allow your cloud users to filter the image list to search what they need,
  for example using a command like this one:

  <pre>openstack image list --property os_distro=debian</pre>

  <h2>How can I verify my download is correct and exactly what has been
    created by Debian?</h2>

  <p>There are files (SHA512SUMS, etc.) which contain
    checksums of the images. These checksum files are also signed - see
    SHA512SUMS.sign, etc. For more information about the verification steps, read
    the <a href="https://www.debian.org/CD/verify">verification guide</a>.
  </p>

  <h2>Other questions?</h2>

  <p>Questions can be forwarded to the Debian Cloud Team: <b>debian-cloud at lists.debian.org</b>.</p>

</div>
  <table id="indexlist">
   <tr class="indexhead"><th class="indexcolicon"><img src="/icons2/blank.png" alt="[ICO]"></th><th class="indexcolname"><a href="?C=N;O=D">Name</a></th><th class="indexcollastmod"><a href="?C=M;O=A">Last modified</a></th><th class="indexcolsize"><a href="?C=S;O=A">Size</a></th></tr>
   <tr class="indexbreakrow"><th colspan="4"><hr></th></tr>
   <tr class="even"><td class="indexcolicon"><a href="/images/"><img src="/icons2/go-previous.png" alt="[PARENTDIR]"></a></td><td class="indexcolname"><a href="/images/">Parent Directory</a></td><td class="indexcollastmod">&nbsp;</td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="OpenStack/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="OpenStack/">OpenStack/</a></td><td class="indexcollastmod">2021-10-10 00:51  </td><td class="indexcolsize">  - </td></tr>
   <tr class="even"><td class="indexcolicon"><a href="bullseye/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="bullseye/">bullseye/</a></td><td class="indexcollastmod">2021-10-11 15:47  </td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="buster-backports/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="buster-backports/">buster-backports/</a></td><td class="indexcollastmod">2021-10-11 22:06  </td><td class="indexcolsize">  - </td></tr>
   <tr class="even"><td class="indexcolicon"><a href="buster/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="buster/">buster/</a></td><td class="indexcollastmod">2021-10-11 22:04  </td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="sid/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="sid/">sid/</a></td><td class="indexcollastmod">2019-07-18 10:34  </td><td class="indexcolsize">  - </td></tr>
   <tr class="even"><td class="indexcolicon"><a href="stretch-backports/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="stretch-backports/">stretch-backports/</a></td><td class="indexcollastmod">2019-07-18 10:40  </td><td class="indexcolsize">  - </td></tr>
   <tr class="odd"><td class="indexcolicon"><a href="stretch/"><img src="/icons2/folder.png" alt="[DIR]"></a></td><td class="indexcolname"><a href="stretch/">stretch/</a></td><td class="indexcollastmod">2019-07-18 10:40  </td><td class="indexcolsize">  - </td></tr>
   <tr class="indexbreakrow"><th colspan="4"><hr></th></tr>
</table>
<address>Apache/2.4.46 (Unix) Server at cloud.debian.org Port 443</address>
</body></html>"""

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_versions(self, urlopen_mock):
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        provider = vmimage.DebianImageProvider()
        self.assertEqual(provider.get_versions(), ['bullseye'])


class OpenSUSEImageProvider(unittest.TestCase):

    #: extracted from https://download.opensuse.org/repositories/Cloud:/Images:/
    VERSION_LISTING = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
 <head>
  <title>Index of /repositories/Cloud:/Images:</title>
  <link rel="stylesheet" href="/icons/index.css" type="text/css" />
<script src="/icons/include/setloc.js" type="text/javascript"></script> </head>
 <body>
<div id="oss-header">
  <div>
    <h1 id="oss-header-title">openSUSE Mirror Index</h1>
    <!-- <a href="/" title="home" id="oss-header-logo">openSUSE Mirror</a> -->
    <h5 id="oss-header-subtitle">Sub domains</h5>
    &nbsp;
    <ul>
      <li><a href="https://www.opensuse.org" title="openSUSE homepage">openSUSE</a></li>
      <li><a href="http://openbuildservice.org/" title="Open Build Service homepage">Open Build Service</a></li>
      <li><a href="https://mirrors.opensuse.org/" title="List of mirror servers">Mirrors</a></li>
      <li><a href="https://software.opensuse.org/" title="Software portal">Software</a></li>
    </ul>
  </div>
  <div id="oss-header-clear"></div>
</div>
<div id="mirrorbrain-details">
<h1>openSUSE download server</h1>
<p>This is the download area of the <a href="https://www.opensuse.org/">openSUSE distribution</a> and the <a href="http://build.opensuse.org/">openSUSE Build Service</a>. If you are searching for a specific package for your distribution, we recommend to use our <a href="https://software.opensuse.org/">Software Portal</a> instead.
<br />
Short overview over the important directories and their content:</p>
  <table>
    <tr><td><a href="/debug/">debug</a> : </td><td><a href="/debug/">debug packages for official released distribution packages</a></td></tr>
    <tr><td><a href="/distribution/">distribution</a> : </td><td><a href="/distribution/">official released openSUSE distributions - online repositories and ISO images</a></td></tr>
    <tr><td><a href="/factory/">factory</a> : </td><td><a href="/factory/">Tumbleweed (former Factory) installation sources and ISO images</a></td></tr>
    <tr><td><a href="/ports/">ports</a> : </td><td><a href="/ports/">ports of the openSUSE distribution</a></td></tr>
    <tr><td><a href="/repositories/">repositories</a> : </td><td><a href="/repositories/">repositories and images created with the Open Build Service</a></td></tr>
    <tr><td><a href="/source/">source</a> : </td><td><a href="/source/">source packages of official released distribution packages</a></td></tr>
    <tr><td><a href="/tumbleweed/">tumbleweed</a> : </td><td><a href="/tumbleweed/">Tumbleweed installation sources and ISO images</a></td></tr>
    <tr><td><a href="/update/">update</a> : </td><td><a href="/update/">updated packages for official released distribution packages</a></td></tr>
  </table>
</div>
<div id="mirrorbrain-wrap">
<h2 id="breadcrumbs">Index of <a href="/">download.opensuse.org</a>/</h2>
<script type="text/javascript">setloc();</script>
<table><tr><th><img src="/icons/blank.gif" alt="[ICO]" width="16" height="16" /></th><th><a href="?C=N;O=D">Name</a></th><th><a href="?C=M;O=A">Last modified</a></th><th><a href="?C=S;O=A">Size</a></th><th>Metadata</th></tr><tr><th colspan="5"><hr /></th></tr>
<tr><td valign="top"><a href="/repositories/Cloud:/"><img src="/icons/up.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="/repositories/Cloud:/">Parent Directory</a></td><td>&nbsp;</td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="Leap_15.0/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="Leap_15.0/">Leap_15.0/</a></td><td align="right">08-Feb-2018 10:04  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="Leap_15.1/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="Leap_15.1/">Leap_15.1/</a></td><td align="right">20-May-2019 19:34  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="Leap_15.2/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="Leap_15.2/">Leap_15.2/</a></td><td align="right">21-Oct-2019 12:09  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="Leap_42.1/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="Leap_42.1/">Leap_42.1/</a></td><td align="right">06-Dec-2016 01:06  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="Leap_42.2/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="Leap_42.2/">Leap_42.2/</a></td><td align="right">06-Dec-2016 13:14  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="Leap_42.3/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="Leap_42.3/">Leap_42.3/</a></td><td align="right">21-Feb-2017 06:49  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="openSUSE_13.1/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="openSUSE_13.1/">openSUSE_13.1/</a></td><td align="right">01-Nov-2017 13:10  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="openSUSE_13.2/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="openSUSE_13.2/">openSUSE_13.2/</a></td><td align="right">01-Nov-2017 13:10  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><td valign="top"><a href="SLES_12.3/"><img src="/icons/folder.png" alt="[DIR]" width="16" height="16" /></a></td><td><a href="SLES_12.3/">SLES_12.3/</a></td><td align="right">01-Nov-2017 13:25  </td><td align="right">  - </td><td>&nbsp;</td></tr>
<tr><th colspan="5"><hr /></th></tr>
</table>
</div>
<div class="oss-header-clear"></div>
<div id="mirrorbrain-footer">
  <a href="https://www.opensuse.org/">openSUSE</a> download area - powered by <a href="http://httpd.apache.org/">Apache</a> and <a href="http://mirrorbrain.org/">MirrorBrain</a>.
  <p>If you find a bug, please report it at: <a href="https://bugzilla.opensuse.org/" target="_blank">https://bugzilla.opensuse.org</a>.
  If you have a server with some space left: <a href='https://en.opensuse.org/openSUSE:Mirror_howto'>become a mirror</a>!</p>
 <p class="text-center">&copy; 2015-2017 SUSE LLC. <span lang="en">All Rights Reserved.</span> <a lang="en" href="https://en.opensuse.org/Imprint">Imprint.</a></p>
</div>
</body></html>
"""

    def setUp(self):
        self.suse_available_versions = ['Leap_15.0', 'Leap_42.1', 'Leap_42.2', 'Leap_42.3']
        self.base_images_url = 'https://download.opensuse.org/repositories/Cloud:/Images:/Leap_15.0/images/'

    @staticmethod
    def get_html_with_image_link(image_link):
        return '''
            <a href="openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.packages"></a>
            <a href="%s"></a>
            <a href="openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.qcow2.sha256"></a>
        ''' % image_link

    def test_get_best_version_default(self):
        suse_latest_version = 15.0
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
        image = 'openSUSE-Leap-15.0-OpenStack.x86_64-0.0.4-Buildlp150.12.30.qcow2'
        html_fixture = self.get_html_with_image_link(image)
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        expected_image_url = self.base_images_url + image

        suse_provider = vmimage.OpenSUSEImageProvider(arch='x86_64')
        suse_provider.get_version = unittest.mock.Mock(return_value='15.0')
        self.assertEqual(suse_provider.get_image_url(), expected_image_url)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_image_url_defining_build(self, urlopen_mock):
        image = 'openSUSE-Leap-15.0-OpenStack.x86_64-1.1.1-Buildlp111.11.11.qcow2'
        html_fixture = self.get_html_with_image_link(image)
        urlread_mocked = unittest.mock.Mock(return_value=html_fixture)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        expected_image_url = self.base_images_url + image

        suse_provider = vmimage.OpenSUSEImageProvider(build='1.1.1-Buildlp111.11.11',
                                                      arch='x86_64')
        suse_provider.get_version = unittest.mock.Mock(return_value='15.0')
        self.assertEqual(suse_provider.get_image_url(), expected_image_url)

    @unittest.mock.patch('avocado.utils.vmimage.urlopen')
    def test_get_versions(self, urlopen_mock):
        urlread_mocked = unittest.mock.Mock(return_value=self.VERSION_LISTING)
        urlopen_mock.return_value = unittest.mock.Mock(read=urlread_mocked)
        provider = vmimage.OpenSUSEImageProvider()
        self.assertEqual(provider.get_versions(),
                         [15.0, 15.1, 15.2, 42.1, 42.2, 42.3])


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
