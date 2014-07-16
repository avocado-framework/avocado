"""
Intermediate module for working with XML-related virsh functions/methods.

The intention of this module is to hide the details of working with XML
from test module code.  Helper methods are all high-level and not
condusive to direct use in error-testing.  However, access to a virsh
instance is available.

All classes defined here should inherit from LibvirtXMLBase and
utilize the property-like interface provided by utils_misc.PropCanBase
to manipulate XML from the 'xml' property. Please refer to the xml_utils
module documentation for more information on working with XMLTreeFile
instances.  Please see the virsh and utils_misc modules for information
on working with Virsh and PropCanBase classes.

All properties defined in __slots__ are intended for test-module
manipulation.  External calling of accessor methods isn't forbidden,
but discouraged. Instead, test modules should use normal reference,
assignment, and delete operations on instance properties as if they
were attributes.  It's up to the test if it uses the dict-like or
instance-attribute interface.

Internally, accessor methods (get_*(), set_*(), & del_*()) should always
use __dict_get__(), __dict_set__(), and/or __dict_del__() to manipulate
properties (otherwise infinite recursion can occur).  In some cases, where
class or instance attributes are needed (ousdie of __slots__) they must
be accessed via the __super_set__(), __super_get__(), and/or __super_del__()
methods. None of the __super_*() or the __dict_*() methods are intended for use
by test-modules.

Errors originating beneath this module (e.g. w/in virsh or libvirt_vm)
should not be caught (so caller can test for them).  Errors detected
within this module should raise LibvirtXMLError or a subclass.
"""

# These are the objects considered for common use:

# all exceptions are siblings of LibvirtXMLError
from virttest.libvirt_xml.xcepts import LibvirtXMLError

from virttest.libvirt_xml.capability_xml import CapabilityXML

from virttest.libvirt_xml.network_xml import RangeList, IPXML, NetworkXML

from virttest.libvirt_xml.vm_xml import VMXML

from virttest.libvirt_xml.pool_xml import SourceXML, PoolXML

from virttest.libvirt_xml.vol_xml import VolXML

from virttest.libvirt_xml.nwfilter_xml import NwfilterXML

from virttest.libvirt_xml.sysinfo_xml import SysinfoXML
