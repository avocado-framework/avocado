=======
vmimage
=======

This utility provides a API to download/cache VM images (QCOW) from the
official distributions repositories.

Basic Usage
===========

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
