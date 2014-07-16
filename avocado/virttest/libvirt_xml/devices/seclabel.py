"""
seclabel device support class(es)

http://libvirt.org/formatdomain.html#seclabel
"""

from virttest.libvirt_xml.devices import base


class Seclabel(base.TypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'seclabel'
    _def_type_name = 'static'
