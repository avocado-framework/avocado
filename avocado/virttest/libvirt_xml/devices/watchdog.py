"""
watchdog device support class(es)

http://libvirt.org/formatdomain.html#elementsWatchdog
"""

from virttest.libvirt_xml.devices import base


class Watchdog(base.UntypedDeviceBase):
    # TODO: Write this class
    __metaclass__ = base.StubDeviceMeta
    _device_tag = 'watchdog'
