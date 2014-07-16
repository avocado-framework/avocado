"""
random number generator device support class(es)

http://libvirt.org/formatdomain.html#elementsRng
"""

from virttest.libvirt_xml.devices import base


class Rng(base.UntypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'rng'
