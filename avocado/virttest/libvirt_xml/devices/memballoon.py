"""
memballoon device support class(es)

http://libvirt.org/formatdomain.html#elementsMemBalloon
"""

from virttest.libvirt_xml.devices import base


class Memballoon(base.UntypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'memballoon'
