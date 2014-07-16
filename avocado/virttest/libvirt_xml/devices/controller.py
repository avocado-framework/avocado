"""
controller device support class(es)

http://libvirt.org/formatdomain.html#elementsControllers
"""

from virttest.libvirt_xml import accessors
from virttest.libvirt_xml.devices import base


class Controller(base.TypedDeviceBase):

    __slots__ = ('type', 'index', 'model', "driver",)

    def __init__(self, type_name, virsh_instance=base.base.virsh):
        super(Controller, self).__init__(device_tag='controller',
                                         type_name=type_name,
                                         virsh_instance=virsh_instance)
        accessors.XMLAttribute('type', self, parent_xpath='/',
                               tag_name='controller', attribute='type')
        accessors.XMLAttribute('index', self, parent_xpath='/',
                               tag_name='controller', attribute='index')
        accessors.XMLAttribute('model', self, parent_xpath='/',
                               tag_name='controller', attribute='model')
        accessors.XMLElementDict('driver', self, parent_xpath='/',
                                 tag_name='driver')
