"""
stp protocl support class(es)

http://libvirt.org/formatnwfilter.html#nwfelemsRulesProtoSTP
"""

from virttest.libvirt_xml import accessors, xcepts
from virttest.libvirt_xml.nwfilter_protocols import base


class Stp(base.TypedDeviceBase):

    """
    Create new Stp xml instances

    Properties:
        attrs: libvirt_xml.nwfilter_protocols.Stp.Attr instance
    """

    __slots__ = ('attrs',)

    def __init__(self, type_name='file', virsh_instance=base.base.virsh):
        accessors.XMLElementNest('attrs', self, parent_xpath='/',
                                 tag_name='stp', subclass=self.Attr,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(Stp, self).__init__(protocol_tag='stp', type_name=type_name,
                                  virsh_instance=virsh_instance)

    def new_attr(self, **dargs):
        """
        Return a new Attr instance and set properties from dargs

        :param dargs: dict of attributes
        :return: new Attr instance
        """
        new_one = self.Attr(virsh_instance=self.virsh)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    def get_attr(self):
        """
        Return stp attribute dict

        :return: None if no stp in xml, dict of stp's attributes.
        """
        try:
            stp_node = self.xmltreefile.reroot('/stp')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
            node = stp_node.getroot()
            stp_attr = dict(node.items())

        return stp_attr

    class Attr(base.base.LibvirtXMLBase):

        """
        Stp attribute XML class

        Properties:

        srcmacaddr: string, MAC address of sender
        srcmacmask: string, Mask applied to MAC address of sender
        type: string, Bridge Protocol Data Unit (BPDU) type
        flags: string, BPDU flag
        root_priority: string, Root priority (range start)
        root_priority_hi: string, Root priority range end
        root_address: string, Root MAC address
        root_address_mask: string, BPDU sender MAC address
        root_cost: string, Root path cost (range start)
        root_cost_hi: string, Root path cost range end
        sender_priority: string, Sender priority (range start)
        sender_priority_hi: string, Sender priority range end
        sender_address: string, BPDU sender MAC address
        sender_address_mask: string, BPDU sender MAC address mask
        port: string, Port identifier (range start)
        port_hi: string, Port identifier range end
        msg_age: string, Message age timer (range start)
        msg_age_hi: string, Message age timer range end
        max_age: string, Maximum age timer (range start)
        max_age_hi: string, Maximum age timer range end
        hello_time: string, Hello time timer (range start)
        hello_time_hi: string, Hello time timer range end
        forward_delay: string, Forward delay (range start)
        forward_delay_hi: string, Forward delay range end
        comment: string, text with max. 256 characters
        """

        __slots__ = ('srcmacaddr', 'srcmacmask', 'type', 'flags',
                     'root_priority', 'root_priority_hi', 'root_address',
                     'root_address_mask', 'root_cost', 'root_cost_hi',
                     'sender_priority', 'sender_priority_hi', 'sender_address',
                     'sender_address_mask', 'port', 'port_hi', 'msg_age',
                     'msg_age_hi', 'max_age', 'max_age_hi', 'hello_time',
                     'hello_time_hi', 'forward_delay', 'forward_delay_hi',
                     'comment')

        def __init__(self, virsh_instance=base.base.virsh):
            accessors.XMLAttribute('srcmacaddr', self, parent_xpath='/',
                                   tag_name='stp', attribute='srcmacaddr')
            accessors.XMLAttribute('srcmacmask', self, parent_xpath='/',
                                   tag_name='stp', attribute='srcmacmask')
            accessors.XMLAttribute('type', self, parent_xpath='/',
                                   tag_name='stp', attribute='type')
            accessors.XMLAttribute('flags', self, parent_xpath='/',
                                   tag_name='stp', attribute='flags')
            accessors.XMLAttribute('root_priority', self, parent_xpath='/',
                                   tag_name='stp', attribute='root-priority')
            accessors.XMLAttribute('root_priority-hi', self, parent_xpath='/',
                                   tag_name='stp', attribute='root-priority-hi')
            accessors.XMLAttribute('root_address', self, parent_xpath='/',
                                   tag_name='stp', attribute='root-address')
            accessors.XMLAttribute('root_address_mask', self,
                                   parent_xpath='/', tag_name='stp',
                                   attribute='root-address-mask')
            accessors.XMLAttribute('root_cost', self, parent_xpath='/',
                                   tag_name='stp', attribute='root-cost')
            accessors.XMLAttribute('root_cost_hi', self, parent_xpath='/',
                                   tag_name='stp', attribute='root-cost-hi')
            accessors.XMLAttribute('sender_priority', self, parent_xpath='/',
                                   tag_name='stp', attribute='sender-priority')
            accessors.XMLAttribute('sender_priority_hi', self,
                                   parent_xpath='/', tag_name='stp',
                                   attribute='sender-priority-hi')
            accessors.XMLAttribute('sender_address', self, parent_xpath='/',
                                   tag_name='stp', attribute='sender-address')
            accessors.XMLAttribute('sender_address_mask', self,
                                   parent_xpath='/', tag_name='stp',
                                   attribute='sender-address-mask')
            accessors.XMLAttribute('port', self, parent_xpath='/',
                                   tag_name='stp', attribute='port')
            accessors.XMLAttribute('port_hi', self, parent_xpath='/',
                                   tag_name='stp', attribute='port_hi')
            accessors.XMLAttribute('msg_age', self, parent_xpath='/',
                                   tag_name='stp', attribute='msg-age')
            accessors.XMLAttribute('msg_age_hi', self, parent_xpath='/',
                                   tag_name='stp', attribute='msg-age-hi')
            accessors.XMLAttribute('max-age', self, parent_xpath='/',
                                   tag_name='stp', attribute='max-age')
            accessors.XMLAttribute('max-age-hi', self, parent_xpath='/',
                                   tag_name='stp', attribute='max-age-hi')
            accessors.XMLAttribute('hello-time', self, parent_xpath='/',
                                   tag_name='stp', attribute='hello-time')
            accessors.XMLAttribute('hello-time-hi', self, parent_xpath='/',
                                   tag_name='stp', attribute='hello-time-hi')
            accessors.XMLAttribute('forward-delay', self, parent_xpath='/',
                                   tag_name='stp', attribute='forward-delay')
            accessors.XMLAttribute('forward-delay-hi', self, parent_xpath='/',
                                   tag_name='stp', attribute='forward-delay-hi')
            accessors.XMLAttribute('comment', self, parent_xpath='/',
                                   tag_name='stp', attribute='comment')

            super(self.__class__, self).__init__(virsh_instance=virsh_instance)
            self.xml = '<stp/>'
