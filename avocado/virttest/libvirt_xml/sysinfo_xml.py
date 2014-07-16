"""
Module simplifying manipulation of sysinfo XML
"""

from virttest.libvirt_xml import base


class SysinfoXML(base.LibvirtXMLBase):

    """
    Handler of libvirt sysinfo xml.
    """

    # TODO: Add more __slots__, accessors and functions to get some useful
    # stats

    __slots__ = []

    def __init__(self, virsh_instance=base.virsh):
        """
        Initialize new instance with empty XML
        """
        super(SysinfoXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = u"<sysinfo></sysinfo>"

    def get_all_processors(self):
        """
        Get all processors dict with entry name as key.

        :return: all processors dict with entry name as key
        """
        processor_dict = {}
        processor_nodes = self.xmltreefile.findall('processor')
        for i in range(len(processor_nodes)):
            temp_dict = {}
            entry_nodes = processor_nodes[i].getchildren()
            if entry_nodes:
                for entry in entry_nodes:
                    entry_attr = dict(entry.items())
                    if entry_attr.has_key('name'):
                        temp_dict[entry_attr['name']] = entry.text
                processor_dict[i] = temp_dict

        return processor_dict
