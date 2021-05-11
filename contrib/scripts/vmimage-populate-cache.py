#!/usr/bin/env python

"""
Script that downloads cloud images via avocado.utils.vmimage
"""

from avocado.core.settings import settings
from avocado.utils import vmimage

KNOWN_IMAGES = (
    # from https://download.cirros-cloud.net/0.4.0/MD5SUMS
    ('cirros', '0.4.0', 'aarch64', 'ecc9a5132e7a0f11a4c585f513cd0873', 'md5'),
    ('cirros', '0.4.0', 'arm', '7e9cfcb763e83573a4b9d9315f56cc5f', 'md5'),
    ('cirros', '0.4.0', 'i386', 'b7d8ac291c698c3f1dc0705ce52a3b64', 'md5'),
    ('cirros', '0.4.0', 'x86_64', '443b7623e27ecf03dc9e01ee93f67afe', 'md5'),
)


def main():
    for image in KNOWN_IMAGES:
        name, version, arch, checksum, algorithm = image
        print("%s version %s (%s): " % (name, version, arch), end='')
        cache_dir = settings.as_dict().get('datadir.paths.cache_dirs')[0]
        download = vmimage.get(name=name, version=version, arch=arch,
                               checksum=checksum, algorithm=algorithm,
                               cache_dir=cache_dir)
        print(download.base_image)


if __name__ == '__main__':
    main()
