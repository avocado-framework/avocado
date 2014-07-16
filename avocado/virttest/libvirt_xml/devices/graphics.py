"""
graphics framebuffer device support class(es)

http://libvirt.org/formatdomain.html#elementsGraphics
"""

from virttest.libvirt_xml import accessors, vm_xml
from virttest.libvirt_xml.devices import base


class Graphics(base.TypedDeviceBase):

    __slots__ = ('passwd', 'channel', 'autoport', 'port', 'tlsPort')

    def __init__(self, type_name='vnc', virsh_instance=base.base.virsh):
        # Add additional attribute 'passwd' for security
        accessors.XMLAttribute('passwd', self, parent_xpath='/',
                               tag_name='graphics', attribute='passwd')
        accessors.XMLAttribute('autoport', self, parent_xpath='/',
                               tag_name='graphics', attribute='autoport')
        accessors.XMLAttribute('port', self, parent_xpath='/',
                               tag_name='graphics', attribute='port')
        accessors.XMLAttribute('tlsPort', self, parent_xpath='/',
                               tag_name='graphics', attribute='tlsPort')
        super(Graphics, self).__init__(device_tag='graphics',
                                       type_name=type_name,
                                       virsh_instance=virsh_instance)

    def get_channel(self):
        """
        Return a list of dictionaries containing each channel's attributes
        """
        return self._get_list('channel')

    def set_channel(self, value):
        """
        Set all channel to the value list of dictionaries of channel attributes
        """
        self._set_list('channel', value)

    def del_channel(self):
        """
        Remove the list of dictionaries containing each channel's attributes
        """
        self._del_list('channel')

    def add_channel(self, **attributes):
        """
        Convenience method for appending channel from dictionary of attributes
        """
        self._add_item('channel', **attributes)

    @staticmethod
    def change_graphic_type_passwd(vm_name, graphic, passwd=None):
        """
        Change the graphic type name and passwd

        :param vm_name: name of vm
        :param graphic: graphic type, spice or vnc
        :param passwd: password for graphic
        """
        vmxml = vm_xml.VMXML.new_from_dumpxml(vm_name)
        devices = vmxml.devices
        graphics = devices.by_device_tag('graphics')[0]
        graphics.type_name = graphic
        if passwd is not None:
            graphics.passwd = passwd
        vmxml.devices = devices
        vmxml.define()

    @staticmethod
    def add_ssl_spice_graphic(vm_name, passwd=None):
        """
        Add spice ssl graphic with passwd

        :param vm_name: name of vm
        :param passwd: password for graphic
        """
        vmxml = vm_xml.VMXML.new_from_dumpxml(vm_name)
        grap = vmxml.get_device_class('graphics')(type_name='spice')
        if passwd is not None:
            grap.passwd = passwd
        grap.autoport = "yes"
        grap.add_channel(name='main', mode='secure')
        grap.add_channel(name='inputs', mode='secure')
        vmxml.devices = vmxml.devices.append(grap)
        vmxml.define()

    @staticmethod
    def del_graphic(vm_name):
        """
        Del original graphic device

        :param vm_name: name of vm
        """
        vmxml = vm_xml.VMXML.new_from_dumpxml(vm_name)
        vmxml.xmltreefile.remove_by_xpath('/devices/graphics')
        vmxml.xmltreefile.write()
        vmxml.define()
