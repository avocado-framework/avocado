avocado.utils.vmimage
=====================

This utility provides an API to download/cache VM images (QCOW) from the
official distributions repositories.

Basic Usage
-----------

Import ``vmimage`` module::

    >>> from avocado.utils import vmimage

Get an image, which consists in an object with the path of the downloaded/cached
base image and the path of the external snapshot created out of that base
image::

    >>> image = vmimage.Image.from_parameters()
    >>> image
    <Image name=Fedora version=35 arch=x86_64>
    >>> image.name
    'Fedora'
    >>> image.path
    '/tmp/by_location/951337e4bd3f30b584623d46f1745147cb32aca5/Fedora-Cloud-Base-35-1.2.x86_64-54d81da8.qcow2'
    >>> image.version
    35
    >>> image.base_image
    '/tmp/by_location/951337e4bd3f30b584623d46f1745147cb32aca5/Fedora-Cloud-Base-35-1.2.x86_64.qcow2'

If you provide more details about the image, the object is expected to
reflect those details::

    >>> image = vmimage.Image.from_parameters(arch='aarch64)
    >>> image
    <Image name=Fedora version=35 arch=aarch64>
    >>> image.name
    'Fedora'
    >>> image.path
    '/tmp/by_location/3f1d3b1b568ad908eb003d1012ba79e1f3bb0d57/Fedora-Cloud-Base-35-1.2.aarch64-dab7007f.qcow2'

    >>> image = vmimage.Image.from_parameters(version=34,name='fedora')
    >>> image
    <Image name=Fedora version=34 arch=x86_64>
    >>> image.path
    '/tmp/by_location/def0ea887952961473cfbfda268e77d66f9bcd14/Fedora-Cloud-Base-34-1.2.x86_64-0ed30cd9.qcow2'

Notice that, unlike the ``base_image`` attribute, the ``path`` attribute
will be always different in each instance, as it actually points to an
external snapshot created out of the base image::

    >>> i1 = vmimage.Image.from_parameters()
    >>> i2 = vmimage.Image.from_parameters()
    >>> i1.path == i2.path
    False

Custom Image Provider
---------------------

If you need your own Image Provider, you can extend the
``vmimage.IMAGE_PROVIDERS`` list, including your provider class. For instance,
using the ``vmimage`` utility in an Avocado test, we could add our own provider
with::

    from avocado import Test

    from avocado.utils import vmimage

    class MyProvider(vmimage.ImageProviderBase):

        name = 'MyDistro'

        def __init__(self, version='[0-9]+', build='[0-9]+.[0-9]+',
                     arch=os.uname()[4]):
            """
            :params version: The regular expression that represents
                             your distro version numbering.
            :params build: The regular expression that represents
                           your build version numbering.
            :params arch: The default architecture to look images for.
            """
            super(MyProvider, self).__init__(version, build, arch)

            # The URL which contains a list of the distro versions
            self.url_versions = 'https://dl.fedoraproject.org/pub/fedora/linux/releases/'

            # The URL which contains a list of distro images
            self.url_images = self.url_versions + '{version}/CloudImages/{arch}/images/'

            # The images naming pattern
            self.image_pattern = 'Fedora-Cloud-Base-{version}-{build}.{arch}.qcow2$'

    class MyTest(Test):

        def setUp(self):
            vmimage.IMAGE_PROVIDERS.add(MyProvider)
            image = vmimage.get('MyDistro')
            ...

        def test(self):
            ...

.. _avocado.utils.vmimage.supported_images:

Supported images
----------------
The vmimage library has no hardcoded limitations of versions or architectures
that can be supported. You can use it as you wish. This is the list of images
that we tested and they work with vmimage:


.. csv-table::
    :file: ./data/vmimage/supported_images.csv
    :header-rows: 1
