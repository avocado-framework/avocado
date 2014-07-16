"""
smartcard device support class(es)

http://libvirt.org/formatdomain.html#elementsSmartcard
"""

from virttest.libvirt_xml.devices import base


class Smartcard(base.UntypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'smartcard'
