"""
video device support class(es)

http://libvirt.org/formatdomain.html#elementsVideo
"""

from virttest.libvirt_xml import accessors
from virttest.libvirt_xml.devices import base


class Video(base.TypedDeviceBase):

    __slots__ = ('model_type', 'model_ram', 'model_vram', 'model_heads',
                 'primary', 'acceleration', 'address')

    def __init__(self, type_name, virsh_instance=base.base.virsh):
        accessors.XMLAttribute('model_type', self,
                               parent_xpath='/',
                               tag_name='model',
                               attribute='type')
        accessors.XMLAttribute('model_ram', self,
                               parent_xpath='/',
                               tag_name='model',
                               attribute='ram')
        accessors.XMLAttribute('model_vram', self,
                               parent_xpath='/',
                               tag_name='model',
                               attribute='vram')
        accessors.XMLAttribute('model_heads', self,
                               parent_xpath='/',
                               tag_name='model',
                               attribute='heads')
        accessors.XMLAttribute('primary', self,
                               parent_xpath='/',
                               tag_name='model',
                               attribute='primary')
        accessors.XMLElementDict('acceleration', self,
                                 parent_xpath='/model',
                                 tag_name='acceleration')
        accessors.XMLElementDict('address', self,
                                 parent_xpath='/',
                                 tag_name='address')
        super(Video, self).__init__(device_tag='video',
                                    type_name=type_name,
                                    virsh_instance=virsh_instance)
