"""
Module simplifying manipulation of XML described at
http://libvirt.org/formatnwfilter.html
"""

from virttest.libvirt_xml import base, xcepts, accessors
from virttest.libvirt_xml.nwfilter_protocols import librarian


class NwfilterRulesProtocol(list):

    """
    List of protocol instances from classes handed out by librarian.get
    """

    @staticmethod
    def __type_check__(other):
        try:
            # Raise error if object isn't dict-like or doesn't have key
            device_tag = other['device_tag']
            # Check that we have support for this type
            librarian.get(device_tag)
        except (AttributeError, TypeError, xcepts.LibvirtXMLError):
            # Required to always raise TypeError for list API in VMXML class
            raise TypeError("Unsupported item type: %s" % str(type(other)))

    def __setitem__(self, key, value):
        self.__type_check__(value)
        super(NwfilterRulesProtocol, self).__setitem__(key, value)
        return self

    def append(self, value):
        self.__type_check__(value)
        super(NwfilterRulesProtocol, self).append(value)
        return self

    def extend(self, iterable):
        # Make sure __type_check__ happens
        for item in iterable:
            self.append(item)
        return self

    def by_device_tag(self, tag):
        result = NwfilterRulesProtocol()
        for protocol in self:
            if protocol.device_tag == tag:
                result.append(protocol)
        return result


class NwfilterXMLRules(base.LibvirtXMLBase):

    """
    Create new NwfilterXMLRules instance.

    Properties:
        rule_action: string, rule action
        rule_direction: string, rule direction
        priority: string, rule priority
        statematch: string, rule statematch
    """

    __slots__ = ('rule_action', 'rule_direction', 'rule_priority',
                 'rule_statematch')

    def __init__(self, protocol=None, virsh_instance=base.virsh):
        accessors.XMLAttribute('rule_action', self, parent_xpath='/',
                               tag_name='rule', attribute='action')
        accessors.XMLAttribute('rule_direction', self, parent_xpath='/',
                               tag_name='rule', attribute='direction')
        accessors.XMLAttribute('rule_priority', self, parent_xpath='/',
                               tag_name='rule', attribute='priority')
        accessors.XMLAttribute('rule_statematch', self, parent_xpath='/',
                               tag_name='rule', attribute='statematch')

        super(NwfilterXMLRules, self).__init__(virsh_instance=virsh_instance)
        self.xml = '<rule></rule>'

    def backup_rule(self):
        """
        Return backup rule instance

        :return: the backup of rule instance
        """
        backup = NwfilterXMLRules(virsh_instance=self.__dict_get__('virsh'))
        backup.xmltreefile = self.xmltreefile.backup_copy()

        return backup

    def get_protocol(self, protocol=None):
        """
        Return None if protocol is None, else return specific class instance

        :param protocol: specific protocol type in rules
        :return: specific protocol class instance from librarian.get
        """
        if protocol:
            protocol_class = librarian.get(protocol)
            protocol_node = self.xmltreefile.getroot().getchildren()[0]
            protocol_node.tag = protocol
            new_one = protocol_class.new_from_element(protocol_node)
            new_one.xmltreefile = self.xmltreefile
        else:
            new_one = None

        return new_one

    def new_protocol(self, **dargs):
        """
        Return a new rule protocol instance and set properties from dargs
        """
        protocol_tag = dargs.get("name")
        new_one = librarian.get(protocol_tag)
        for key, value in dargs.items():
            setattr(new_one, key, value)
        return new_one

    def del_protocol(self):
        """
        Delete protocol in rule xml
        """
        protocol_node = self.xmltreefile.getroot().getchildren()
        if protocol_node:
            self.xmltreefile.remove(protocol_node[0])
            self.xmltreefile.write()


class NwfilterXMLBase(base.LibvirtXMLBase):

    """
    Accessor methods for NwfilterXML class.

    Properties:
        filter_name: string, filter name
        filter_chain: string, filter name
        filter_priority: string, filter priority
        uuid: string, operates on uuid tag
        filterref: string, operates on filterref tag
        filterref_name: string, reference filter name
    """

    __slots__ = base.LibvirtXMLBase.__slots__ + ('filter_name', 'filter_chain',
                                                 'filter_priority',
                                                 'uuid', 'filterref',
                                                 'filterref_name')

    __uncompareable__ = base.LibvirtXMLBase.__uncompareable__

    __schema_name__ = "nwfilter"

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLAttribute('filter_name', self, parent_xpath='/',
                               tag_name='filter', attribute='name')
        accessors.XMLAttribute('filter_chain', self, parent_xpath='/',
                               tag_name='filter', attribute='chain')
        accessors.XMLAttribute('filter_priority', self, parent_xpath='/',
                               tag_name='filter', attribute='priority')
        accessors.XMLElementText('uuid', self, parent_xpath='/',
                                 tag_name='uuid')
        accessors.XMLElementText('filterref', self, parent_xpath='/',
                                 tag_name='filterref')
        accessors.XMLAttribute('filterref_name', self, parent_xpath='/',
                               tag_name='filterref', attribute='filter')

        super(NwfilterXMLBase, self).__init__(virsh_instance=virsh_instance)

    def get_rule_index(self, rule_protocol=None):
        """
        Return rule index list for specific protocol

        :param rule_protocol: the specific protocol type in rules
        :return: rule index list
        """
        rule_index = []
        source_root = self.xmltreefile.findall('rule')
        for i in range(len(source_root)):
            if rule_protocol:
                protocol_node = source_root[i].getchildren()[0]
                if protocol_node.tag == rule_protocol:
                    rule_index.append(i)
            else:
                rule_index.append(i)

        return rule_index

    def get_rule(self, rule_index=0, rule_protocol=None):
        """
        Return NwfilterXMLRules instance for specific protocol and index

        :param rule_index: rule's index number
        :param rule_protocol: the specific protocol type in rules
        :return: New initialized NwfilterXMLRules instance
        """
        index = self.get_rule_index(rule_protocol)
        if rule_index not in index:
            raise xcepts.LibvirtXMLError("rule index %s is not valid" %
                                         rule_index)
        source_root = self.xmltreefile.findall('rule')
        rulexml = NwfilterXMLRules(virsh_instance=self.__dict_get__('virsh'))
        rulexml.xmltreefile = self.xmltreefile.backup_copy()
        rulexml.xmltreefile._setroot(source_root[rule_index])
        rulexml.xmltreefile.write()
        rulexml.xmltreefile.flush()

        return rulexml

    def del_rule(self, rule_index=0):
        """
        Delete rule with specific index

        :param rule_index: rule's index number
        """
        source_root = self.xmltreefile.findall('rule')
        self.xmltreefile.remove(source_root[rule_index])
        self.xmltreefile.write()

    def set_rule(self, value, rule_index=0):
        """
        Delete rule with specific index and add new given value

        :param rule_index: rule's index number
        :param value: NwfilterXMLRules instance
        """
        if not issubclass(type(value), NwfilterXMLRules):
            raise xcepts.LibvirtXMLError(
                "Value must be a NwfilterXMLRules or subclass")
        try:
            source_root = self.xmltreefile.findall('rule')
        except KeyError, detail:
            raise xcepts.LibvirtXMLError(detail)
        if source_root[rule_index] is not None:
            self.del_rule(rule_index)
        root = self.xmltreefile.getroot()
        root.insert(rule_index, value.xmltreefile.getroot())
        self.xmltreefile.write()

    def add_rule(self, value):
        """
        Add new rule into filter

        :param value: NwfilterXMLRules instance
        """
        if not issubclass(type(value), NwfilterXMLRules):
            raise xcepts.LibvirtXMLError(
                "Value must be a NwfilterXMLRules or subclass")
        root = self.xmltreefile.getroot()
        root.append(value.xmltreefile.getroot())
        self.xmltreefile.write()

    def get_protocol_attr(self, rule_index=0, protocol=None):
        """
        Return protocol dict of specific rule index and protocol type

        :param rule_index: rule's index number
        :param protocol: the specific protocol type in rules
        :return: protocol attribute dict
        """
        rule = self.get_rule(rule_index, protocol)
        if protocol:
            protocol = rule.get_protocol(protocol)
            attr = protocol.get_attr()
        else:
            attr = None

        return attr


class NwfilterXML(NwfilterXMLBase):

    """
    Manipulators of a nwfilter through it's XML definition.
    """

    __slots__ = NwfilterXMLBase.__slots__

    def __init__(self, virsh_instance=base.virsh):
        """
        Initialize new instance with empty XML
        """
        super(NwfilterXML, self).__init__(virsh_instance=virsh_instance)
        self.xml = u"<filter></filter>"

    @staticmethod
    def new_from_filter_dumpxml(uuid, options="", virsh_instance=base.virsh):
        """
        Return new NwfilterXML instance from virsh filter-dumpxml command

        :param uuid: filter's uuid
        :param virsh_instance: virsh module or instance to use
        :return: New initialized NwfilterXML instance
        """
        filter_xml = NwfilterXML(virsh_instance=virsh_instance)
        filter_xml['xml'] = virsh_instance.nwfilter_dumpxml(uuid,
                                                            options=options
                                                            ).stdout.strip()

        return filter_xml

    def get_all_rules(self):
        """
        Return all rules dict with protocol attribute.

        :return: all rules dict with key as rule index number
        """
        rule_dict_attr = {}
        rule_nodes = self.xmltreefile.findall('rule')
        for i in range(len(rule_nodes)):
            if rule_nodes[i].getchildren():
                protocol_node = rule_nodes[i].getchildren()[0]
                protocol = protocol_node.tag
                pro_dict = dict(protocol_node.items())
                rule_dict = dict(rule_nodes[i].items())
                rule_dict.update(pro_dict)
                rule_dict['protocol'] = protocol
                rule_dict_attr[i] = rule_dict
            else:
                rule_dict = dict(rule_nodes[i].items())
                rule_dict_attr[i] = rule_dict

        return rule_dict_attr

    def get_rules_dict(self, filter_name, options="",
                       virsh_instance=base.virsh):
        """
        Return all rules dict with protocol attribute for given filter

        :param filter_name: name or uuid of filter
        :param options: extra options
        :return: all rules dictionary with index as key
        """
        filxml = NwfilterXML.new_from_filter_dumpxml(filter_name,
                                                     virsh_instance=base.virsh)
        rules = filxml.get_all_rules()

        return rules

    def get_all_protocols(self, protocol=None):
        """
        Put all type of protocol into a NwfilterRulesProtocol instance.
        Return all protocols class list if protocol as None, else return
        specific protocol type class list.

        :param protocol: specific protocol type in rules
        :return: NwfilterRulesProtocol instance list
        """
        protocols = NwfilterRulesProtocol()
        all_rules = self.xmltreefile.findall('rule')

        for i in all_rules:
            protocol_node = i.getchildren()
            if protocol_node:
                if protocol:
                    # Each rule node only have one protocol node, so
                    # only use protocol_node[0]
                    if protocol_node[0].tag == protocol:
                        protocol_class = librarian.get(protocol)
                        new_one = protocol_class.new_from_element(
                            protocol_node[0])
                        protocols.device_tag = protocol
                        protocols.append(new_one)
                else:
                    protocol_class = librarian.get(protocol_node[0].tag)
                    new_one = protocol_class.new_from_element(
                        protocol_node[0])
                    protocols.device_tag = protocol_node[0].tag
                    protocols.append(new_one)

        return protocols
