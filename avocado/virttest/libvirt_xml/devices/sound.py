"""
sound device support class(es)

http://libvirt.org/formatdomain.html#elementsSound
"""

from virttest.libvirt_xml.devices import base


class Sound(base.UntypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'sound'
