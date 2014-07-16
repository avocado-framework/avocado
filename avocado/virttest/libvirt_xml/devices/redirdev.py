"""
redirdev device support class(es)

http://libvirt.org/formatdomain.html#elementsRedir
"""

from virttest.libvirt_xml.devices import base


class Redirdev(base.TypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'redirdev'
    _def_type_name = 'spicevmc'
