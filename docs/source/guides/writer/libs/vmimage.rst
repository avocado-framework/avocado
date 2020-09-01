avocado.utils.vmimage
=====================

This utility provides a API to download/cache VM images (QCOW) from the
official distributions repositories.

Basic Usage
-----------

Import ``vmimage`` module::

    >>> from avocado.utils import vmimage

Get an image, which consists in an object with the path of the dowloaded/cached
base image and the path of the external snapshot created out of that base
image::

    >>> image = vmimage.get()
    >>> image
    <Image name=Fedora version=26 arch=x86_64>
    >>> image.name
    'Fedora'
    >>> image.path
    '/tmp/Fedora-Cloud-Base-26-1.5.x86_64-d369c285.qcow2'
    >>> image.get()
    '/tmp/Fedora-Cloud-Base-26-1.5.x86_64-e887c743.qcow2'
    >>> image.path
    '/tmp/Fedora-Cloud-Base-26-1.5.x86_64-e887c743.qcow2'
    >>> image.version
    26
    >>> image.base_image
    '/tmp/Fedora-Cloud-Base-26-1.5.x86_64.qcow2'

If you provide more details about the image, the object is expected to
reflect those details::

    >>> image = vmimage.get(arch='aarch64')
    >>> image
    <Image name=FedoraSecondary version=26 arch=aarch64>
    >>> image.name
    'FedoraSecondary'
    >>> image.path
    '/tmp/Fedora-Cloud-Base-26-1.5.aarch64-07b8fbda.qcow2'

    >>> image = vmimage.get(version=7)
    >>> image
    <Image name=CentOS version=7 arch=x86_64>
    >>> image.path
    '/tmp/CentOS-7-x86_64-GenericCloud-1708-dd8139c5.qcow2'

Notice that, unlike the ``base_image`` attribute, the ``path`` attribute
will be always different in each instance, as it actually points to an
external snapshot created out of the base image::

    >>> i1 = vmimage.get()
    >>> i2 = vmimage.get()
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
