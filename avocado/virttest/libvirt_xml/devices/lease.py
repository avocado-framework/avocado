"""
lease device support class(es)

http://libvirt.org/formatdomain.html#elementsLease
"""

from virttest.libvirt_xml.devices import base


class Lease(base.UntypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'lease'
