"""
Module simplifying manipulation of XML described at
http://libvirt.org/formatdomain.html
"""

import logging
from autotest.client.shared import error
from virttest import xml_utils
from virttest.libvirt_xml import base, accessors, xcepts
from virttest.libvirt_xml.devices import librarian


class VMXMLDevices(list):

    """
    List of device instances from classes handed out by librarian.get()
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
        super(VMXMLDevices, self).__setitem__(key, value)
        return self

    def append(self, value):
        self.__type_check__(value)
        super(VMXMLDevices, self).append(value)
        return self

    def extend(self, iterable):
        # Make sure __type_check__ happens
        for item in iterable:
            self.append(item)
        return self

    def by_device_tag(self, tag):
        result = VMXMLDevices()
        for device in self:
            if device.device_tag == tag:
                result.append(device)
        return result


class VMXMLBase(base.LibvirtXMLBase):

    """
    Accessor methods for VMXML class properties (items in __slots__)

    Properties:
        hypervisor_type: string, hypervisor type name
            get: return domain's type attribute value
            set: change domain type attribute value
            del: raise xcepts.LibvirtXMLError
        vm_name: string, name of the vm
            get: return text value of name tag
            set: set text value of name tag
            del: raise xcepts.LibvirtXMLError
        uuid: string, uuid string for vm
            get: return text value of uuid tag
            set: set text value for (new) uuid tag (unvalidated)
            del: remove uuid tag
        vcpu, max_mem, current_mem: integers
            get: returns integer
            set: set integer
            del: removes tag
        numa: dictionary
            get: return dictionary of numatune/memory attributes
            set: set numatune/memory attributes from dictionary
            del: remove numatune/memory tag
        devices: VMXMLDevices (list-like)
            get: returns VMXMLDevices instance for all devices
            set: Define all devices from VMXMLDevices instance
            del: remove all devices
        cputune: VMCPUTune
            get: return VMCPUTune instance for the domain.
            set: Define cputune tag from a VMCPUTune instance.
            del: remove cputune tag
        current_vcpu: string, 'current' attribute of vcpu tag
            get: return a string for 'current' attribute of vcpu
            set: change 'current' attribute of vcpu
            del: remove 'current' attribute of vcpu
        placement: string, 'placement' attribute of vcpu tag
            get: return a string for 'placement' attribute of vcpu
            set: change 'placement' attribute of vcpu
            del: remove 'placement' attribute of vcpu
        emulatorpin: string, cpuset value (see man virsh: cpulist)
            get: return text value of cputune/emulatorpin attributes
            set: set cputune/emulatorpin attributes from string
            del: remove cputune/emulatorpin tag
    """

    # Additional names of attributes and dictionary-keys instances may contain
    __slots__ = ('hypervisor_type', 'vm_name', 'uuid', 'vcpu', 'max_mem',
                 'current_mem', 'numa', 'devices', 'seclabel',
                 'cputune', 'placement', 'current_vcpu', 'os', 'os_type',
                 'os_arch', 'os_init', 'os_boot', 'os_loader', 'os_bios',
                 'pm')

    __uncompareable__ = base.LibvirtXMLBase.__uncompareable__

    __schema_name__ = "domain"

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLAttribute(property_name="hypervisor_type",
                               libvirtxml=self,
                               forbidden=None,
                               parent_xpath='/',
                               tag_name='domain',
                               attribute='type')
        accessors.XMLElementText(property_name="vm_name",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/',
                                 tag_name='name')
        accessors.XMLElementText(property_name="uuid",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/',
                                 tag_name='uuid')
        accessors.XMLElementInt(property_name="vcpu",
                                libvirtxml=self,
                                forbidden=None,
                                parent_xpath='/',
                                tag_name='vcpu')
        accessors.XMLAttribute(property_name="current_vcpu",
                               libvirtxml=self,
                               forbidden=None,
                               parent_xpath='/',
                               tag_name='vcpu',
                               attribute='current')
        accessors.XMLAttribute(property_name="placement",
                               libvirtxml=self,
                               forbidden=None,
                               parent_xpath='/',
                               tag_name='vcpu',
                               attribute='placement')
        accessors.XMLElementInt(property_name="max_mem",
                                libvirtxml=self,
                                forbidden=None,
                                parent_xpath='/',
                                tag_name='memory')
        accessors.XMLElementInt(property_name="current_mem",
                                libvirtxml=self,
                                forbidden=None,
                                parent_xpath='/',
                                tag_name='currentMemory')
        accessors.XMLElementText(property_name="os",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/',
                                 tag_name='os')
        accessors.XMLElementText(property_name="os_type",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/os',
                                 tag_name='type')
        accessors.XMLAttribute(property_name="os_arch",
                               libvirtxml=self,
                               forbidden=None,
                               parent_xpath='/os',
                               tag_name='type',
                               attribute='arch')
        accessors.XMLElementDict(property_name="os_boot",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/os',
                                 tag_name='boot')
        accessors.XMLElementText(property_name="os_init",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/os',
                                 tag_name='init')
        accessors.XMLElementText(property_name="os_loader",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/os',
                                 tag_name='loader')
        accessors.XMLElementDict(property_name="os_bios",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='/os',
                                 tag_name='bios')
        accessors.XMLElementDict(property_name="numa",
                                 libvirtxml=self,
                                 forbidden=None,
                                 parent_xpath='numatune',
                                 tag_name='memory')
        accessors.XMLElementNest(property_name='cputune',
                                 libvirtxml=self,
                                 parent_xpath='/',
                                 tag_name='cputune',
                                 subclass=VMCPUTune,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        accessors.XMLElementNest(property_name='pm',
                                 libvirtxml=self,
                                 parent_xpath='/',
                                 tag_name='pm',
                                 subclass=VMPM,
                                 subclass_dargs={
                                     'virsh_instance': virsh_instance})
        super(VMXMLBase, self).__init__(virsh_instance=virsh_instance)

    def get_devices(self, device_type=None):
        """
        Put all nodes of devices into a VMXMLDevices instance.
        """
        devices = VMXMLDevices()
        all_devices = self.xmltreefile.find('devices')
        if device_type is not None:
            device_nodes = all_devices.findall(device_type)
        else:
            device_nodes = all_devices
        for node in device_nodes:
            device_tag = node.tag
            device_class = librarian.get(device_tag)
            new_one = device_class.new_from_element(node,
                                                    virsh_instance=self.virsh)
            devices.append(new_one)
        return devices

    def set_devices(self, value):
        """
        Define devices based on contents of VMXMLDevices instance
        """
        value_type = type(value)
        if not issubclass(value_type, VMXMLDevices):
            raise xcepts.LibvirtXMLError("Value %s Must be a VMXMLDevices or "
                                         "subclass not a %s"
                                         % (str(value), str(value_type)))
        # Start with clean slate
        exist_dev = self.xmltreefile.find('devices')
        if exist_dev is not None:
            self.del_devices()
        if len(value) > 0:
            devices_element = xml_utils.ElementTree.SubElement(
                self.xmltreefile.getroot(), 'devices')
            for device in value:
                # Separate the element from the tree
                device_element = device.xmltreefile.getroot()
                devices_element.append(device_element)
        self.xmltreefile.write()

    def del_devices(self):
        """
        Remove all devices
        """
        self.xmltreefile.remove_by_xpath('/devices')
        self.xmltreefile.write()

    def get_seclabel(self):
        """
        Return seclabel + child attribute dict or raise LibvirtXML error

        :return: None if no seclabel in xml,
                 dict of seclabel's attributs and children.
        """
        __children_list__ = ['label', 'baselabel', 'imagelabel']

        seclabel_node = self.xmltreefile.find("seclabel")
        # no seclabel tag found in xml.
        if seclabel_node is None:
            raise xcepts.LibvirtXMLError("Seclabel for this domain does not "
                                         "exist")
        seclabel = dict(seclabel_node.items())
        for child_name in __children_list__:
            child_node = seclabel_node.find(child_name)
            if child_node is not None:
                seclabel[child_name] = child_node.text

        return seclabel

    def set_seclabel(self, seclabel_dict):
        """
        Set seclabel of vm. Modify the attributs and children if seclabel
        exists and create a new seclabel if seclabel is not found in
        xmltreefile.
        """
        __attributs_list__ = ['type', 'model', 'relabel']
        __children_list__ = ['label', 'baselabel', 'imagelabel']

        # check the type of seclabel_dict.
        if not isinstance(seclabel_dict, dict):
            raise xcepts.LibvirtXMLError("seclabel_dict should be a instance of"
                                         "dict, but not a %s.\n"
                                         % type(seclabel_dict))
        seclabel_node = self.xmltreefile.find("seclabel")
        if seclabel_node is None:
            seclabel_node = xml_utils.ElementTree.SubElement(
                self.xmltreefile.getroot(),
                "seclabel")

        for key, value in seclabel_dict.items():
            if key in __children_list__:
                child_node = seclabel_node.find(key)
                if child_node is None:
                    child_node = xml_utils.ElementTree.SubElement(
                        seclabel_node,
                        key)
                child_node.text = value

            elif key in __attributs_list__:
                seclabel_node.set(key, value)

            else:
                continue

        self.xmltreefile.write()

    def del_seclabel(self):
        """
        Remove the seclabel tag from a domain
        """
        try:
            self.xmltreefile.remove_by_xpath("/seclabel")
        except (AttributeError, TypeError):
            pass  # Element already doesn't exist
        self.xmltreefile.write()


class VMXML(VMXMLBase):

    """
    Higher-level manipulations related to VM's XML or guest/host state
    """

    # Must copy these here or there will be descriptor problems
    __slots__ = []

    def __init__(self, hypervisor_type='kvm', virsh_instance=base.virsh):
        """
        Create new VM XML instance
        """
        super(VMXML, self).__init__(virsh_instance=virsh_instance)
        # Setup some bare-bones XML to build upon
        self.xml = u"<domain type='%s'></domain>" % hypervisor_type

    @staticmethod  # static method (no self) needed b/c calls VMXML.__new__
    def new_from_dumpxml(vm_name, options="", virsh_instance=base.virsh):
        """
        Return new VMXML instance from virsh dumpxml command

        :param vm_name: Name of VM to dumpxml
        :param virsh_instance: virsh module or instance to use
        :return: New initialized VMXML instance
        """
        # TODO: Look up hypervisor_type on incoming XML
        vmxml = VMXML(virsh_instance=virsh_instance)
        vmxml['xml'] = virsh_instance.dumpxml(vm_name,
                                              extra=options).stdout.strip()
        return vmxml

    @staticmethod
    def new_from_inactive_dumpxml(vm_name, options="", virsh_instance=base.virsh):
        """
        Return new VMXML instance of inactive domain from virsh dumpxml command

        :param vm_name: Name of VM to dumpxml
        :param options: virsh dumpxml command's options
        :param virsh_instance: virsh module or instance to use
        :return: New initialized VMXML instance
        """
        if options.find("--inactive") == -1:
            options += " --inactive"
        return VMXML.new_from_dumpxml(vm_name, options, virsh_instance)

    @staticmethod
    def get_device_class(type_name):
        """
        Return class that handles type_name devices, or raise exception.
        """
        return librarian.get(type_name)

    def undefine(self, options=None):
        """Undefine this VM with libvirt retaining XML in instance"""
        return self.virsh.remove_domain(self.vm_name, options)

    def define(self):
        """Define VM with virsh from this instance"""
        result = self.virsh.define(self.xml)
        if result.exit_status:
            logging.debug("Define %s failed.\n"
                          "Detail: %s.", self.vm_name, result.stderr)
            return False
        return True

    def sync(self, options=None):
        """Rebuild VM with the config file."""
        # If target vm no longer exist, this will raise an exception.
        try:
            backup = self.new_from_dumpxml(self.vm_name)
        except IOError:
            logging.debug("Failed to backup %s.", self.vm_name)
            backup = None

        if not self.undefine(options):
            raise xcepts.LibvirtXMLError("Failed to undefine %s."
                                         % self.vm_name)
        if not self.define():
            if backup:
                backup.define()
            raise xcepts.LibvirtXMLError("Failed to define %s, from %s."
                                         % (self.vm_name, self.xml))

    @staticmethod
    def vm_rename(vm, new_name, uuid=None, virsh_instance=base.virsh):
        """
        Rename a vm from its XML.

        :param vm: VM class type instance
        :param new_name: new name of vm
        :param uuid: new_vm's uuid, if None libvirt will generate.
        :return: a new VM instance
        """
        if vm.is_alive():
            vm.destroy(gracefully=True)
        vmxml = VMXML.new_from_dumpxml(vm_name=vm.name,
                                       virsh_instance=virsh_instance)
        backup = vmxml.copy()
        # can't do in-place rename, must operate on XML
        if not vmxml.undefine():
            del vmxml  # clean up temporary files
            raise xcepts.LibvirtXMLError("Error reported while undefining VM")
        # Alter the XML
        vmxml.vm_name = new_name
        if uuid is None:
            # invalidate uuid so libvirt will regenerate
            del vmxml.uuid
            vm.uuid = None
        else:
            vmxml.uuid = uuid
            vm.uuid = uuid
        # Re-define XML to libvirt
        logging.debug("Rename %s to %s.", vm.name, new_name)
        # error message for failed define
        error_msg = "Error reported while defining VM:\n"
        try:
            if not vmxml.define():
                raise xcepts.LibvirtXMLError(error_msg + "%s"
                                             % vmxml.get('xml'))
        except error.CmdError, detail:
            del vmxml  # clean up temporary files
            # Allow exceptions thrown here since state will be undefined
            backup.define()
            raise xcepts.LibvirtXMLError(error_msg + "%s" % detail)
        # Keep names uniform
        vm.name = new_name
        return vm

    @staticmethod
    def set_pm_suspend(vm_name, mem="yes", disk="yes", virsh_instance=base.virsh):
        """
        Add/set pm suspend Support

        :params vm_name: Name of defined vm
        :params mem: Enable suspend to memory
        :params disk: Enable suspend to disk
        """
        # Build a instance of class VMPM.
        pm = VMPM()
        pm.mem_enabled = mem
        pm.disk_enabled = disk
        # Set pm to the new instance.
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        vmxml.pm = pm
        vmxml.sync()

    @staticmethod
    def set_vm_vcpus(vm_name, value, current=None, virsh_instance=base.virsh):
        """
        Convenience method for updating 'vcpu' and 'current' attribute property
        of a defined VM

        :param vm_name: Name of defined vm to change vcpu elemnet data
        :param value: New data value, None to delete.
        :param current: New current value, None will not change current value
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        if value is not None:
            if current is not None:
                if current > value:
                    raise xcepts.LibvirtXMLError(
                        "The cpu current value %s is larger than max number %s"
                        % (current, value))
                else:
                    vmxml['vcpu'] = value  # call accessor method to change XML
                    vmxml['current_vcpu'] = current
        else:  # value is None
            del vmxml.vcpu
        vmxml.undefine()
        vmxml.define()
        # Temporary files for vmxml cleaned up automatically
        # when it goes out of scope here.

    @staticmethod
    def check_cpu_mode(mode):
        """
        Check input cpu mode invalid or not.

        :param mode: the mode of cpu:'host-model'...
        """
        # Possible values for the mode attribute are:
        # "custom", "host-model", "host-passthrough"
        cpu_mode = ["custom", "host-model", "host-passthrough"]
        if mode.strip() not in cpu_mode:
            raise xcepts.LibvirtXMLError(
                "The cpu mode '%s' is invalid!" % mode)

    def get_disk_all(self):
        """
        Return VM's disk from XML definition, None if not set
        """
        disk_nodes = self.xmltreefile.find('devices').findall('disk')
        disks = {}
        for node in disk_nodes:
            dev = node.find('target').get('dev')
            disks[dev] = node
        return disks

    @staticmethod
    def get_disk_source(vm_name, option="", virsh_instance=base.virsh):
        """
        Get block device  of a defined VM's disks.

        :param vm_name: Name of defined vm.
        :param option: extra option.
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, option,
                                       virsh_instance=virsh_instance)
        disks = vmxml.get_disk_all()
        return disks.values()

    @staticmethod
    def get_disk_blk(vm_name, virsh_instance=base.virsh):
        """
        Get block device  of a defined VM's disks.

        :param vm_name: Name of defined vm.
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        disks = vmxml.get_disk_all()
        return disks.keys()

    @staticmethod
    def get_disk_count(vm_name, virsh_instance=base.virsh):
        """
        Get count of VM's disks.

        :param vm_name: Name of defined vm.
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        disks = vmxml.get_disk_all()
        if disks is not None:
            return len(disks)
        return 0

    @staticmethod
    def check_disk_exist(vm_name, disk_src, virsh_instance=base.virsh):
        """
        Check if given disk exist in VM.

        :param vm_name: Domain name.
        :param disk_src: Domian disk source path or darget dev.
        :return: True/False
        """
        found = False
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        if not vmxml.get_disk_count(vm_name, virsh_instance=virsh_instance):
            raise xcepts.LibvirtXMLError("No disk in domain %s." % vm_name)
        blk_list = vmxml.get_disk_blk(vm_name, virsh_instance=virsh_instance)
        disk_list = vmxml.get_disk_source(vm_name, virsh_instance=virsh_instance)
        try:
            file_list = []
            for disk in disk_list:
                file_list.append(disk.find('source').get('file'))
        except AttributeError:
            logging.debug("No 'file' type disk.")
        if disk_src in file_list + blk_list:
            found = True
        return found

    @staticmethod
    def check_disk_type(vm_name, disk_src, disk_type, virsh_instance=base.virsh):
        """
        Check if disk type is correct in VM

        :param vm_name: Domain name.
        :param disk_src: Domain disk source path
        :param disk_type: Domain disk type
        :return: True/False
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        if not vmxml.get_disk_count(vm_name, virsh_instance=virsh_instance):
            raise xcepts.LibvirtXMLError("No disk in domain %s." % vm_name)
        disks = vmxml.get_disk_source(vm_name, virsh_instance=virsh_instance)

        found = False
        try:
            for disk in disks:
                disk_dev = ""
                if disk_type == "file":
                    disk_dev = disk.find('source').get('file')
                elif disk_type == "block":
                    disk_dev = disk.find('source').get('dev')
                if disk_src == disk_dev:
                    found = True
        except AttributeError:
            logging.debug("No '%s' type disk." % disk_type)

        return found

    @staticmethod
    def get_disk_serial(vm_name, disk_target, virsh_instance=base.virsh):
        """
        Get disk serial in VM

        :param vm_name: Domain name.
        :param disk_target: Domain disk target
        :return: disk serial
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        if not vmxml.get_disk_count(vm_name, virsh_instance=virsh_instance):
            raise xcepts.LibvirtXMLError("No disk in domain %s." % vm_name)
        try:
            disk = vmxml.get_disk_all()[disk_target]
        except KeyError:
            raise xcepts.LibvirtXMLError("Wrong disk target:%s." % disk_target)
        serial = ""
        try:
            serial = disk.find("serial").text
        except AttributeError:
            logging.debug("No serial assigned.")

        return serial

    @staticmethod
    def get_disk_address(vm_name, disk_target, virsh_instance=base.virsh):
        """
        Get disk address in VM

        :param vm_name: Domain name.
        :param disk_target: Domain disk target
        :return: disk address
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        if not vmxml.get_disk_count(vm_name, virsh_instance=virsh_instance):
            raise xcepts.LibvirtXMLError("No disk in domain %s." % vm_name)
        try:
            disk = vmxml.get_disk_all()[disk_target]
        except KeyError:
            raise xcepts.LibvirtXMLError("Wrong disk target:%s." % disk_target)
        address_str = ""
        try:
            address = disk.find("address")
            add_type = address.get("type")
            add_domain = address.get("domain")
            add_bus = address.get("bus")
            add_slot = address.get("slot")
            add_func = address.get("function")
            address_str = ("%s:%s.%s.%s.%s"
                           % (add_type, add_domain, add_bus,
                              add_slot, add_func))
        except AttributeError, e:
            raise xcepts.LibvirtXMLError("Get wrong attribute: %s" % str(e))
        return address_str

    @staticmethod
    def get_numa_params(vm_name, virsh_instance=base.virsh):
        """
        Return VM's numa setting from XML definition
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        return vmxml.numa

    def get_primary_serial(self):
        """
        Get a dict with primary serial features.
        """
        xmltreefile = self.__dict_get__('xml')
        primary_serial = xmltreefile.find('devices').find('serial')
        serial_features = {}
        serial_type = primary_serial.get('type')
        serial_port = primary_serial.find('target').get('port')
        # Support node here for more features
        serial_features['serial'] = primary_serial
        # Necessary features
        serial_features['type'] = serial_type
        serial_features['port'] = serial_port
        return serial_features

    @staticmethod
    def set_primary_serial(vm_name, dev_type, port, path=None,
                           virsh_instance=base.virsh):
        """
        Set primary serial's features of vm_name.

        :param vm_name: Name of defined vm to set primary serial.
        :param dev_type: the type of ``serial:pty,file...``
        :param port: the port of serial
        :param path: the path of serial, it is not necessary for pty
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        xmltreefile = vmxml.__dict_get__('xml')
        try:
            serial = vmxml.get_primary_serial()['serial']
        except AttributeError:
            logging.debug("Can not find any serial, now create one.")
            # Create serial tree, default is pty
            serial = xml_utils.ElementTree.SubElement(
                xmltreefile.find('devices'),
                'serial', {'type': 'pty'})
            # Create elements of serial target, default port is 0
            xml_utils.ElementTree.SubElement(serial, 'target', {'port': '0'})

        serial.set('type', dev_type)
        serial.find('target').set('port', port)
        # path may not be exist.
        if path is not None:
            serial.find('source').set('path', path)
        else:
            try:
                source = serial.find('source')
                serial.remove(source)
            except AssertionError:
                pass  # Element not found, already removed.
        xmltreefile.write()
        vmxml.set_xml(xmltreefile.name)
        vmxml.undefine()
        vmxml.define()

    @staticmethod
    def set_agent_channel(vm_name):
        """
        Add channel for guest agent running

        :param vm_name: Name of defined vm to set agent channel
        """
        vmxml = VMXML.new_from_dumpxml(vm_name)

        try:
            exist = vmxml.__dict_get__('xml').find('devices').findall('channel')
            findc = 0
            for ec in exist:
                if ec.find('target').get('name') == "org.qemu.guest_agent.0":
                    findc = 1
                    break
            if findc == 0:
                raise AttributeError("Cannot find guest agent channel")
        except AttributeError:
            channel = vmxml.get_device_class('channel')(type_name='unix')
            channel.add_source(mode='bind',
                               path='/var/lib/libvirt/qemu/guest.agent')
            channel.add_target(type='virtio',
                               name='org.qemu.guest_agent.0')
            vmxml.devices = vmxml.devices.append(channel)
            vmxml.define()

    @staticmethod
    def remove_agent_channel(vm_name):
        """
        Delete channel for guest agent

        :param vm_name: Name of defined vm to remove agent channel
        """
        vmxml = VMXML.new_from_dumpxml(vm_name)

        try:
            exist = vmxml.__dict_get__('xml').find('devices').findall('channel')
            for ec in exist:
                if ec.find('target').get('name') == "org.qemu.guest_agent.0":
                    channel = vmxml.get_device_class('channel')(type_name='unix')
                    channel.add_source(mode='bind',
                                       path=ec.find('source').get('path'))
                    channel.add_target(type='virtio',
                                       name=ec.find('target').get('name'))
                    vmxml.del_device(channel)
            vmxml.define()
        except AttributeError:
            raise xcepts.LibvirtXMLError("Fail to remove agent channel!")

    def get_iface_all(self):
        """
        Get a dict with interface's mac and node.
        """
        iface_nodes = self.xmltreefile.find('devices').findall('interface')
        interfaces = {}
        for node in iface_nodes:
            mac_addr = node.find('mac').get('address')
            interfaces[mac_addr] = node
        return interfaces

    @staticmethod
    def get_iface_by_mac(vm_name, mac, virsh_instance=base.virsh):
        """
        Get the interface if mac is matched.

        :param vm_name: Name of defined vm.
        :param mac: a mac address.
        :return: return a dict include main interface's features
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        interfaces = vmxml.get_iface_all()
        try:
            interface = interfaces[mac]
        except KeyError:
            interface = None
        if interface is not None:  # matched mac exists.
            iface_type = interface.get('type')
            source = interface.find('source').get(iface_type)
            features = {}
            features['type'] = iface_type
            features['mac'] = mac
            features['source'] = source
            return features
        else:
            return None

    @staticmethod
    def get_iface_dev(vm_name, virsh_instance=base.virsh):
        """
        Return VM's interface device from XML definition, None if not set
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        ifaces = vmxml.get_iface_all()
        if ifaces:
            return ifaces.keys()
        return None

    @staticmethod
    def get_first_mac_by_name(vm_name, virsh_instance=base.virsh):
        """
        Convenience method for getting first mac of a defined VM

        :param: vm_name: Name of defined vm to get mac
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, virsh_instance=virsh_instance)
        xmltreefile = vmxml.__dict_get__('xml')
        try:
            iface = xmltreefile.find('devices').find('interface')
            return iface.find('mac').get('address')
        except AttributeError:
            return None

    @staticmethod
    def get_iftune_params(vm_name, options="", virsh_instance=base.virsh):
        """
        Return VM's interface tuning setting from XML definition
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, options=options,
                                       virsh_instance=virsh_instance)
        xmltreefile = vmxml.__dict_get__('xml')
        iftune_params = {}
        bandwidth = None
        try:
            bandwidth = xmltreefile.find('devices/interface/bandwidth')
            try:
                iftune_params['inbound'] = bandwidth.find(
                    'inbound').get('average')
                iftune_params['outbound'] = bandwidth.find(
                    'outbound').get('average')
            except AttributeError:
                logging.error("Can't find <inbound> or <outbound> element")
        except AttributeError:
            logging.error("Can't find <bandwidth> element")

        return iftune_params

    def get_net_all(self):
        """
        Return VM's net from XML definition, None if not set
        """
        xmltreefile = self.__dict_get__('xml')
        net_nodes = xmltreefile.find('devices').findall('interface')
        nets = {}
        for node in net_nodes:
            dev = node.find('target').get('dev')
            nets[dev] = node
        return nets

    # TODO re-visit this method after the libvirt_xml.devices.interface module
    #     is implemented
    @staticmethod
    def get_net_dev(vm_name):
        """
        Get net device of a defined VM's nets.

        :param vm_name: Name of defined vm.
        """
        vmxml = VMXML.new_from_dumpxml(vm_name)
        nets = vmxml.get_net_all()
        if nets is not None:
            return nets.keys()
        return None

    @staticmethod
    def set_cpu_mode(vm_name, mode='host-model'):
        """
        Set cpu's mode of VM.

        :param vm_name: Name of defined vm to set cpu mode.
        :param mode: the mode of cpu:'host-model'...
        """
        vmxml = VMXML.new_from_dumpxml(vm_name)
        vmxml.check_cpu_mode(mode)
        xmltreefile = vmxml.__dict_get__('xml')
        try:
            cpu = xmltreefile.find('/cpu')
            logging.debug("Current cpu mode is '%s'!", cpu.get('mode'))
            cpu.set('mode', mode)
        except AttributeError:
            logging.debug("Can not find any cpu, now create one.")
            cpu = xml_utils.ElementTree.SubElement(xmltreefile.getroot(),
                                                   'cpu', {'mode': mode})
        xmltreefile.write()
        vmxml.undefine()
        vmxml.define()

    def add_device(self, value):
        """
        Add a device into VMXML.

        :param value: instance of device in libvirt_xml/devices/
        """
        devices = self.get_devices()
        for device in devices:
            if device == value:
                logging.debug("Device %s is already in VM %s.", value, self)
                return
        devices.append(value)
        self.set_devices(devices)

    def del_device(self, value):
        """
        Remove a device from VMXML

        :param value: instance of device in libvirt_xml/devices/
        """
        devices = self.get_devices()
        not_found = True
        for device in devices:
            if device == value:
                not_found = False
                devices.remove(device)
                break
        if not_found:
            logging.debug("Device %s does not exist in VM %s.", value, self)
            return
        self.set_devices(devices)

    @staticmethod
    def add_security_info(vmxml, passwd):
        """
        Add passwd for graphic

        :param vmxml: instance of VMXML
        :param passwd: Password you want to set
        """
        devices = vmxml.devices
        graphics_index = devices.index(devices.by_device_tag('graphics')[0])
        graphics = devices[graphics_index]
        graphics.passwd = passwd
        vmxml.devices = devices
        vmxml.define()

    def add_hostdev(self, source_address, mode='subsystem',
                    type='pci',
                    managed='yes'):
        """
        Add a hostdev device to guest.
        """
        dev = self.get_device_class('hostdev')()
        dev.mode = mode
        dev.type = type
        dev.managed = managed
        dev.source_address = source_address
        self.add_device(dev)

    @staticmethod
    def get_blkio_params(vm_name, options="", virsh_instance=base.virsh):
        """
        Return VM's block I/O setting from XML definition
        """
        vmxml = VMXML.new_from_dumpxml(vm_name, options=options,
                                       virsh_instance=virsh_instance)
        xmltreefile = vmxml.__dict_get__('xml')
        blkio_params = {}
        try:
            blkio = xmltreefile.find('blkiotune')
            try:
                blkio_params['weight'] = blkio.find('weight').text
            except AttributeError:
                logging.error("Can't find <weight> element")
        except AttributeError:
            logging.error("Can't find <blkiotune> element")

        if blkio and blkio.find('device'):
            blkio_params['device_weights_path'] = \
                blkio.find('device').find('path').text
            blkio_params['device_weights_weight'] = \
                blkio.find('device').find('weight').text

        return blkio_params


class VMCPUXML(VMXML):

    """
    Higher-level manipulations related to VM's XML(CPU)
    """

    # Must copy these here or there will be descriptor problems
    __slots__ = ('model', 'vendor', 'feature_list',)

    def __init__(self, virsh_instance=base.virsh, vm_name='', mode='host-model'):
        """
        Create new VMCPU XML instance
        """
        # The set action is for test.
        accessors.XMLElementText(property_name="model",
                                 libvirtxml=self,
                                 forbidden=['del'],
                                 parent_xpath='/cpu',
                                 tag_name='model')
        accessors.XMLElementText(property_name="vendor",
                                 libvirtxml=self,
                                 forbidden=['del'],
                                 parent_xpath='/cpu',
                                 tag_name='vendor')
        # This will skip self.get_feature_list() defined below
        accessors.AllForbidden(property_name="feature_list",
                               libvirtxml=self)
        super(VMCPUXML, self).__init__(virsh_instance=virsh_instance)
        # Setup some bare-bones XML to build upon
        self.set_cpu_mode(vm_name, mode)
        self['xml'] = self.__dict_get__('virsh').dumpxml(vm_name,
                                                         extra="--update-cpu").stdout.strip()

    def get_feature_list(self):
        """
        Accessor method for feature_list property (in __slots__)
        """
        feature_list = []
        xmltreefile = self.__dict_get__('xml')
        for feature_node in xmltreefile.findall('/cpu/feature'):
            feature_list.append(feature_node)
        return feature_list

    def get_feature_name(self, num):
        """
        Get assigned feature name

        :param num: Assigned feature number
        :return: Assigned feature name
        """
        count = len(self.feature_list)
        if num >= count:
            raise xcepts.LibvirtXMLError("Get %d from %d features"
                                         % (num, count))
        feature_name = self.feature_list[num].get('name')
        return feature_name

    def remove_feature(self, num):
        """
        Remove a assigned feature from xml

        :param num: Assigned feature number
        """
        xmltreefile = self.__dict_get__('xml')
        count = len(self.feature_list)
        if num >= count:
            raise xcepts.LibvirtXMLError("Remove %d from %d features"
                                         % (num, count))
        feature_remove_node = self.feature_list[num]
        cpu_node = xmltreefile.find('/cpu')
        cpu_node.remove(feature_remove_node)

    @staticmethod
    def check_feature_name(value):
        """
        Check feature name valid or not.

        :param value: The feature name
        :return: True if check pass
        """
        sys_feature = []
        cpu_xml_file = open('/proc/cpuinfo', 'r')
        for line in cpu_xml_file.readline():
            if line.find('flags') != -1:
                feature_names = line.split(':')[1].strip()
                sys_sub_feature = feature_names.split(' ')
                sys_feature = list(set(sys_feature + sys_sub_feature))
        return (value in sys_feature)

    def set_feature(self, num, value):
        """
        Set a assigned feature value to xml

        :param num: Assigned feature number
        :param value: The feature name modified to
        """
        count = len(self.feature_list)
        if num >= count:
            raise xcepts.LibvirtXMLError("Set %d from %d features"
                                         % (num, count))
        feature_set_node = self.feature_list[num]
        feature_set_node.set('name', value)

    def add_feature(self, value):
        """
        Add a feature Element to xml

        :param num: Assigned feature number
        """
        xmltreefile = self.__dict_get__('xml')
        cpu_node = xmltreefile.find('/cpu')
        xml_utils.ElementTree.SubElement(cpu_node, 'feature', {'name': value})


class VMClockXML(VMXML):

    """
    Higher-level manipulations related to VM's XML(Clock)
    """

    # Must copy these here or there will be descriptor problems
    __slots__ = ('offset', 'timezone', 'adjustment', 'timers')

    def __init__(self, virsh_instance=base.virsh, offset="utc"):
        """
        Create new VMClock XML instance
        """
        # The set action is for test.
        accessors.XMLAttribute(property_name="offset",
                               libvirtxml=self,
                               forbidden=[],
                               parent_xpath='/',
                               tag_name='clock',
                               attribute='offset')
        accessors.XMLAttribute(property_name="timezone",
                               libvirtxml=self,
                               forbidden=[],
                               parent_xpath='/',
                               tag_name='clock',
                               attribute='timezone')
        accessors.XMLAttribute(property_name="adjustment",
                               libvirtxml=self,
                               forbidden=[],
                               parent_xpath='/',
                               tag_name='clock',
                               attribute='adjustment')
        accessors.XMLElementList(property_name="timers",
                                 libvirtxml=self,
                                 forbidden=[],
                                 parent_xpath="/clock",
                                 marshal_from=self.marshal_from_timer,
                                 marshal_to=self.marshal_to_timer)
        super(VMClockXML, self).__init__(virsh_instance=virsh_instance)
        # Set default offset for clock
        self.offset = offset

    def from_dumpxml(self, vm_name, virsh_instance=base.virsh):
        """Helper to load xml from domain."""
        self.xml = VMXML.new_from_dumpxml(vm_name,
                                          virsh_instance=virsh_instance).xml

    # Sub-element of clock
    class Timer(VMXML):

        """Timer element of clock"""

        __slots__ = ('name', 'present')

        def __init__(self, virsh_instance=base.virsh, timer_name="tsc"):
            """
            Create new Timer XML instance
            """
            # The set action is for test.
            accessors.XMLAttribute(property_name="name",
                                   libvirtxml=self,
                                   forbidden=[],
                                   parent_xpath='/clock',
                                   tag_name='timer',
                                   attribute='name')
            accessors.XMLAttribute(property_name="present",
                                   libvirtxml=self,
                                   forbidden=[],
                                   parent_xpath='/clock',
                                   tag_name='timer',
                                   attribute='present')
            super(VMClockXML.Timer, self).__init__(virsh_instance=virsh_instance)
            # name is mandatory for timer
            self.name = timer_name

        def update(self, attr_dict):
            for attr, value in attr_dict.items():
                setattr(self, attr, value)

    @staticmethod
    def marshal_from_timer(item, index, libvirtxml):
        """Convert a Timer instance into tag + attributes"""
        del index
        del libvirtxml
        timer = item.xmltreefile.find("clock/timer")
        try:
            return (timer.tag, dict(timer.items()))
        except AttributeError:  # Didn't find timer
            raise xcepts.LibvirtXMLError("Expected a list of timer "
                                         "instances, not a %s" % str(item))

    @staticmethod
    def marshal_to_timer(tag, attr_dict, index, libvirtxml):
        """Convert a tag + attributes to a Timer instance"""
        del index
        if tag == 'timer':
            newone = VMClockXML.Timer(virsh_instance=libvirtxml.virsh)
            newone.update(attr_dict)
            return newone
        else:
            return None


class VMCPUTune(base.LibvirtXMLBase):

    """
    CPU tuning tag XML class

    Elements:
        vcpupins:             list of dict - vcpu, cpuset
        emulatorpin:          attribute    - cpuset
        shares:               int
        period:               int
        quota:                int
        emulator_period:      int
        emulator_quota:       int
    """

    __slots__ = ('vcpupins', 'emulatorpin', 'shares', 'period', 'quota',
                 'emulator_period', 'emulator_quota')

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLElementList('vcpupins', self, parent_xpath='/',
                                 marshal_from=self.marshal_from_vcpupins,
                                 marshal_to=self.marshal_to_vcpupins)
        accessors.XMLAttribute('emulatorpin', self, parent_xpath='/',
                               tag_name='emulatorpin', attribute='cpuset')
        for slot in self.__all_slots__:
            if slot in ('shares', 'period', 'quota', 'emulator_period',
                        'emulator_quota'):
                accessors.XMLElementInt(slot, self, parent_xpath='/',
                                        tag_name=slot)
        super(self.__class__, self).__init__(virsh_instance=virsh_instance)
        self.xml = '<cputune/>'

    @staticmethod
    def marshal_from_vcpupins(item, index, libvirtxml):
        """
        Convert a dict to vcpupin tag and attributes.
        """
        del index
        del libvirtxml
        if not isinstance(item, dict):
            raise xcepts.LibvirtXMLError("Expected a dictionary of host "
                                         "attributes, not a %s"
                                         % str(item))
        return ('vcpupin', dict(item))

    @staticmethod
    def marshal_to_vcpupins(tag, attr_dict, index, libvirtxml):
        """
        Convert a vcpupin tag and attributes to a dict.
        """
        del index
        del libvirtxml
        if tag != 'vcpupin':
            return None
        return dict(attr_dict)


class VMPM(base.LibvirtXMLBase):

    """
    VM power management tag XML class

    Elements:
        suspend-to-disk:        attribute    - enabled
        suspend-to-mem:         attribute    - enabled
    """

    __slots__ = ('disk_enabled', 'mem_enabled')

    def __init__(self, virsh_instance=base.virsh):
        accessors.XMLAttribute('disk_enabled', self, parent_xpath='/',
                               tag_name='suspend-to-disk', attribute='enabled')
        accessors.XMLAttribute('mem_enabled', self, parent_xpath='/',
                               tag_name='suspend-to-mem', attribute='enabled')
        super(self.__class__, self).__init__(virsh_instance=virsh_instance)
        self.xml = '<pm/>'
