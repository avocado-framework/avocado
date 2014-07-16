"""
filesystem device support class(es)

http://libvirt.org/formatdomain.html#elementsFilesystems
"""

from virttest.libvirt_xml.devices import base


class Filesystem(base.TypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'filesystem'
    _def_type_name = 'file'
