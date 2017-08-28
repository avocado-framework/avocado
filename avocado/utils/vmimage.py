import os
import tempfile
import uuid

try:
    import lzma
except:
    pass

from . import asset
from . import process
from . import path as utils_path


QEMU_IMG = utils_path.find_command('qemu-img')
VIRT_CUSTOMIZE = utils_path.find_command('virt-customize')


class Image(object):

    def __init__(self, name, major, minor, build, arch, checksum, algorithm,
                 cache_dir):
        self.name = name
        self.major = major
        self.minor = minor
        self.build = build
        self.arch = arch
        self.checksum = checksum
        self.algorithm = algorithm
        if cache_dir is None:
            cache_dir = tempfile.gettempdir()
        self.cache_dir = cache_dir
        self.username = None
        self.password = None
        self.path = None
        self._drop_cloud_init = False
        self.get()

    def get(self):
        asset_path = asset.Asset(name=self.url,
                                 asset_hash=self.checksum,
                                 algorithm=self.algorithm,
                                 locations=None,
                                 cache_dirs=[self.cache_dir],
                                 expire=None).fetch()

        if os.path.splitext(asset_path)[1] == '.xz':
            asset_path = self._extract(asset_path)

        self.path = self._create_backed_image(asset_path)

    def set_credentials(self, username, password):
        cmd = ('%s -a %s --password %s:password:%s' %
               (VIRT_CUSTOMIZE, self.path, username, password))
        if self._drop_cloud_init:
            cmd += ' --uninstall cloud-init'
        process.run(cmd)
        self.username = username
        self.password = password

    def remove(self):
        self.path = None
        os.remove(self.path)

    @staticmethod
    def _create_backed_image(source_image):
        new_image = '%s-%s' % (source_image, uuid.uuid4())
        cmd = '%s create -f qcow2 -b %s %s' % (QEMU_IMG,
                                               source_image,
                                               new_image)
        process.run(cmd)
        return new_image

    @staticmethod
    def _extract(path, force=False):
        extracted_file = os.path.splitext(path)[0]
        if not force and os.path.exists(extracted_file):
            return extracted_file
        with open(path, 'r') as file_obj:
            with open(extracted_file, 'wb') as newfile_obj:
                newfile_obj.write(lzma.decompress(file_obj.read()))
        return extracted_file


class CentOS(Image):
    def __init__(self, major, build, arch='x86_64', checksum=None,
                 algorithm=None, cache_dir=None):
        url = ('https://cloud.centos.org/'
               'centos/{major}/images/'
               'CentOS-{major}-{arch}-GenericCloud-{build}.qcow2.xz')
        self.url = url.format(major=major, build=build, arch=arch)

        super(CentOS, self).__init__(name='CentOS',
                                     major=major,
                                     minor=None,
                                     build=build,
                                     arch=arch,
                                     checksum=checksum,
                                     algorithm=algorithm,
                                     cache_dir=cache_dir)


class Fedora(Image):
    def __init__(self, major, minor, build, arch='x86_64', checksum=None,
                 algorithm=None, cache_dir=None):
        url = ('https://download.fedoraproject.org/'
               'pub/fedora/linux/releases/{major}/CloudImages/{arch}/images/'
               'Fedora-Cloud-Base-{major}-{minor}.{build}.{arch}.qcow2')
        self.url = url.format(major=major, minor=minor, build=build, arch=arch)

        super(Fedora, self).__init__(name='CentOS',
                                     major=major,
                                     minor=None,
                                     build=build,
                                     arch=arch,
                                     checksum=checksum,
                                     algorithm=algorithm,
                                     cache_dir=cache_dir)
        self._drop_cloud_init = True


class Ubuntu(Image):
    def __init__(self, major, minor, arch='amd64', checksum=None,
                 algorithm=None, cache_dir=None):
        url = ('https://cloud-images.ubuntu.com/'
               'releases/{major}.{minor}/release/'
               'ubuntu-{major}.{minor}-server-cloudimg-{arch}.img')
        self.url = url.format(major=major, minor=minor, arch=arch)

        super(Ubuntu, self).__init__(name='Ubuntu',
                                     major=major,
                                     minor=minor,
                                     build=None,
                                     arch=arch,
                                     checksum=checksum,
                                     algorithm=algorithm,
                                     cache_dir=cache_dir)
