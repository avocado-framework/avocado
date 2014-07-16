"""
Specializations of base.AccessorBase for particular XML manipulation types
"""

import logging
import re
import sys
from virttest import xml_utils
from virttest.propcan import PropCanBase
from virttest.libvirt_xml import xcepts, base
# The backports module will take care of picking the builtin if available
from virttest.staging.backports import bin


def type_check(name, thing, expected):
    """
    Check that thing is expected subclass or instance, raise ValueError if not
    """
    is_a = type(thing)
    is_a_name = str(is_a)
    if not isinstance(expected, list):
        expected = [expected]
    for e in expected:
        try:
            it_is = issubclass(thing, e)
        except TypeError:
            it_is = isinstance(thing, e)
        if it_is:
            return
    raise ValueError('%s value is not any of %s, it is a %s'
                     % (name, expected, is_a_name))


def add_to_slots(*args):
    """
    Return list of AccessorBase.__all_slots__ + args
    """
    for slot in args:
        type_check('slot name', slot, str)
    return AccessorBase.__all_slots__ + args


class AccessorBase(PropCanBase):

    """
    Base class for a callable operating on a LibvirtXMLBase subclass instance
    """

    # Gets AccessorGeneratorBase subclass's required_accessor_data_keys added
    __slots__ = ('operation', 'property_name', 'libvirtxml')

    def __init__(self, operation, property_name, libvirtxml, **dargs):
        """
        Initialize accessor to operate on lvxml with accessor_data for property

        :param operation: Debug String for 'Getter', 'Setter', or 'Delter'
        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param dargs: Necessary for subclasses to extend required parameters
        """
        type_check('Parameter property_name', property_name, str)
        type_check('Operation attribute', operation, str)
        type_check('__slots__ attribute', self.__all_slots__, [tuple, list])
        type_check('Parameter libvirtxml', libvirtxml, base.LibvirtXMLBase)

        super(AccessorBase, self).__init__()

        self.__dict_set__('operation', operation)
        self.__dict_set__('property_name', property_name)
        self.__dict_set__('libvirtxml', libvirtxml)

        for slot in self.__all_slots__:
            if slot in AccessorBase.__all_slots__:
                continue  # already checked these
            # Don't care about value type
            if slot not in dargs:
                raise ValueError('Required accessor generator parameter %s'
                                 % slot)
            self.__dict_set__(slot, dargs[slot])

    # Subclass expected to override this and specify parameters
    __call__ = NotImplementedError

    def __repr__(self):
        return ("%s's %s for %s with %s"
                % (self.libvirtxml.__class__.__name__, self.operation,
                   self.property_name, str(dict(self))))

    def xmltreefile(self):
        """
        Retrieve xmltreefile instance from libvirtxml instance
        """
        return self.libvirtxml.xmltreefile

    def element_by_parent(self, parent_xpath, tag_name, create=True):
        """
        Retrieve/create an element instance at parent_xpath/tag_name

        :param parent_xpath: xpath of parent element
        :param tag_name: name of element under parent to retrieve/create
        :param create: True to create new element if not exist
        :return: ElementTree.Element instance
        :raise: LibvirtXMLError: If element not exist & create=False
        """
        type_check('parent_xpath', parent_xpath, str)
        type_check('tag_name', tag_name, str)
        parent_element = self.xmltreefile().find(parent_xpath)
        if (parent_element == self.xmltreefile().getroot() and
                parent_element.tag == tag_name):
            return parent_element
        excpt_str = ('Exception thrown from %s for property "%s" while'
                     ' looking for element tag "%s", on parent at xpath'
                     ' "%s", in XML\n%s\n' % (self.operation,
                                              self.property_name, tag_name, parent_xpath,
                                              str(self.xmltreefile())))
        if parent_element is None:
            if create:
                # This will only work for simple XPath strings
                self.xmltreefile().create_by_xpath(parent_xpath)
                parent_element = self.xmltreefile().find(parent_xpath)
            # if create or not, raise if not exist
            if parent_element is None:
                raise xcepts.LibvirtXMLAccessorError(excpt_str)
        try:
            element = parent_element.find(tag_name)
        except:
            logging.error(excpt_str)
            raise
        if element is None:
            if create:  # Create the element
                element = xml_utils.ElementTree.SubElement(parent_element,
                                                           tag_name)
            else:  # create is False
                raise xcepts.LibvirtXMLNotFoundError('Error in %s for property '
                                                     '"%s", element tag "%s" not '
                                                     'found on parent at xpath "%s"'
                                                     ' in XML\n%s\n'
                                                     % (self.operation,
                                                        self.property_name,
                                                        tag_name, parent_xpath,
                                                        str(self.xmltreefile())))
        return element


class ForbiddenBase(AccessorBase):

    """
    Raise LibvirtXMLAccessorError when called w/ or w/o a value arg.
    """

    __slots__ = []

    def __call__(self, value=None):
        if value:
            raise xcepts.LibvirtXMLForbiddenError("%s %s to '%s' on %s "
                                                  "forbidden"
                                                  % (self.operation,
                                                     self.property_name,
                                                     str(value),
                                                     str(self)))
        else:
            raise xcepts.LibvirtXMLForbiddenError("%s %s on %s "
                                                  "forbidden"
                                                  % (self.operation,
                                                     self.property_name,
                                                     str(self)))


class AccessorGeneratorBase(object):

    """
    Accessor method/class generator for specific property name
    """

    def __init__(self, property_name, libvirtxml, forbidden=None, **dargs):
        """
        Initialize accessor methods, marking operations in forbidden as such

        :param property_name: Name of the property
        :param libvirtxml: Instance reference to LibvirtXMLBase subclass
        :param forbidden: Optional string list of 'get', 'set', and/or 'del'
        :param dargs: Specific AccessorGeneratorBase subclass info.
        """
        if forbidden is None:
            forbidden = []
        type_check('forbidden', forbidden, list)
        self.forbidden = forbidden

        type_check('libvirtxml', libvirtxml, base.LibvirtXMLBase)
        self.libvirtxml = libvirtxml

        type_check('property_name', property_name, str)
        self.property_name = property_name

        self.dargs = dargs

        # Lookup all property names possibly needing accessors
        for operation in ('get', 'set', 'del'):
            self.set_if_not_defined(operation)

    def set_if_not_defined(self, operation):
        """
        Setup a callable instance for operation only if not already defined
        """
        # Don't overwrite methods in libvirtxml instance
        if not hasattr(self.libvirtxml, self.accessor_name(operation)):
            if operation not in self.forbidden:
                self.assign_callable(operation, self.make_callable(operation))
            else:  # operation is forbidden
                self.assign_callable(operation, self.make_forbidden(operation))

    def accessor_name(self, operation):
        """
        Return instance name for operation, defined by subclass (i.e. 'get_foo')
        """
        return "%s_%s" % (operation, self.property_name)

    @staticmethod
    def callable_name(operation):
        """
        Return class name for operation (i.e. 'Getter'), defined by subclass.
        """
        return operation.capitalize() + 'ter'

    def make_callable(self, operation):
        """
        Return an callable instance for operation
        """
        callable_class = getattr(self, self.callable_name(operation))
        return callable_class(
            self.callable_name(operation), self.property_name,
            self.libvirtxml, **self.dargs)

    def make_forbidden(self, operation):
        """
        Return a forbidden callable instance for operation
        """
        return ForbiddenBase(operation, self.property_name, self.libvirtxml)

    def assign_callable(self, operation, callable_inst):
        """
        Set reference on objectified libvirtxml instance to callable_inst
        """
        self.libvirtxml.__super_set__(self.accessor_name(operation),
                                      callable_inst)


# Implementation of specific accessor generator subclasses follows


class AllForbidden(AccessorGeneratorBase):

    """
    Class of forbidden accessor classes for those undefined on libvirtxml
    """

    def __init__(self, property_name, libvirtxml):
        """
        Create exception raising accessors for those undefined on libvirtxml

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        """
        super(AllForbidden, self).__init__(property_name=property_name,
                                           libvirtxml=libvirtxml,
                                           forbidden=['get', 'set', 'del'])


class XMLElementText(AccessorGeneratorBase):

    """
    Class of accessor classes operating on element.text
    """

    required_dargs = ('parent_xpath', 'tag_name')

    def __init__(self, property_name, libvirtxml, forbidden=None,
                 parent_xpath=None, tag_name=None):
        """
        Create undefined accessors on libvirt instance

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param forbidden: Optional list of 'get', 'set', 'del'
        :param parent_xpath: XPath string of parent element
        :param tag_name: element tag name to manipulate text attribute on.
        """
        super(XMLElementText, self).__init__(property_name, libvirtxml,
                                             forbidden,
                                             parent_xpath=parent_xpath,
                                             tag_name=tag_name)

    class Getter(AccessorBase):

        """
        Retrieve text on element
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name')

        def __call__(self):
            return self.element_by_parent(self.parent_xpath,
                                          self.tag_name, create=False).text

    class Setter(AccessorBase):

        """
        Set text to value on element
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name')

        def __call__(self, value):
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=True)
            element.text = str(value)
            self.xmltreefile().write()

    class Delter(AccessorBase):

        """
        Remove element and ignore if it doesn't exist (same as False)
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name')

        def __call__(self):
            try:
                element = self.element_by_parent(self.parent_xpath,
                                                 self.tag_name, create=False)
            except (xcepts.LibvirtXMLNotFoundError,  # element doesn't exist
                    xcepts.LibvirtXMLAccessorError):  # parent doesn't exist
                pass  # already gone
            else:
                parent = self.xmltreefile().find(self.parent_xpath)
                if parent is not None:
                    parent.remove(element)
                    self.xmltreefile().write()


class XMLElementInt(AccessorGeneratorBase):

    """
    Class of accessor classes operating on element.text as an integer
    """
    __radix2func_dict__ = {0: int,
                           2: bin,
                           8: oct,
                           10: int,
                           16: hex}

    required_dargs = ('parent_xpath', 'tag_name', 'radix')

    def __init__(self, property_name, libvirtxml, forbidden=None,
                 parent_xpath=None, tag_name=None, radix=10):
        """
        Create undefined accessors on libvirt instance

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param forbidden: Optional list of 'Getter', 'Setter', 'Delter'
        :param parent_xpath: XPath string of parent element
        :param tag_name: element tag name to manipulate text attribute on.
        """
        try:
            self.__radix2func_dict__[radix]
        except KeyError:
            raise xcepts.LibvirtXMLError("Param radix=%s for XMLElementInt "
                                         "is not accepted." % radix)
        super(XMLElementInt, self).__init__(property_name, libvirtxml,
                                            forbidden,
                                            parent_xpath=parent_xpath,
                                            tag_name=tag_name,
                                            radix=radix)

    class Getter(AccessorBase):

        """
        Retrieve text on element and convert to int
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name', 'radix')

        def __call__(self):
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=False)
            try:
                result = int(element.text, self.radix)
            except ValueError:
                raise xcepts.LibvirtXMLError("Value of %s in %s is %s,"
                                             "not a Integer." % (self.tag_name,
                                                                 self.parent_xpath, element.text))
            return result

    class Setter(AccessorBase):

        """
        Set text on element after converting to int then to str
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name', 'radix')

        def __call__(self, value):
            type_check(self.property_name + ' value', value, int)
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=True)
            convertFunc = XMLElementInt.__radix2func_dict__[self.radix]
            element.text = str(convertFunc(value))
            self.xmltreefile().write()

    Delter = XMLElementText.Delter


class XMLElementBool(AccessorGeneratorBase):

    """
    Class of accessor classes operating purely element existence
    """

    required_dargs = ('parent_xpath', 'tag_name')

    def __init__(self, property_name, libvirtxml, forbidden=None,
                 parent_xpath=None, tag_name=None):
        """
        Create undefined accessors on libvirt instance

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param forbidden: Optional list of 'get', 'set', 'del'
        :param parent_xpath: XPath string of parent element
        :param tag_name: element tag name to manipulate text attribute on.
        """
        super(XMLElementBool, self).__init__(property_name, libvirtxml,
                                             forbidden,
                                             parent_xpath=parent_xpath,
                                             tag_name=tag_name)

    class Getter(AccessorBase):

        """
        Retrieve text on element
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name')

        def __call__(self):
            try:
                # Throws exception if parent path or element not exist
                self.element_by_parent(self.parent_xpath, self.tag_name,
                                       create=False)
                return True
            except (xcepts.LibvirtXMLAccessorError,
                    xcepts.LibvirtXMLNotFoundError):
                return False

    class Setter(AccessorBase):

        """
        Create element when True, delete when false
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name')

        def __call__(self, value):
            if bool(value) is True:
                self.element_by_parent(self.parent_xpath, self.tag_name,
                                       create=True)
            else:
                delattr(self.libvirtxml, self.property_name)
            self.xmltreefile().write()

    Delter = XMLElementText.Delter


class XMLAttribute(AccessorGeneratorBase):

    """
    Class of accessor classes operating on an attribute of an element
    """

    def __init__(self, property_name, libvirtxml, forbidden=None,
                 parent_xpath=None, tag_name=None, attribute=None):
        """
        Create undefined accessors on libvirt instance

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param forbidden: Optional list of 'Getter', 'Setter', 'Delter'
        :param parent_xpath: XPath string of parent element
        :param tag_name: element tag name to manipulate text attribute on.
        :param attribute: Attribute name to manupulate
        """
        super(XMLAttribute, self).__init__(property_name, libvirtxml,
                                           forbidden, parent_xpath=parent_xpath,
                                           tag_name=tag_name, attribute=attribute)

    class Getter(AccessorBase):

        """
        Get attribute value
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name', 'attribute')

        def __call__(self):
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=False)
            value = element.get(self.attribute, None)
            if value is None:
                raise xcepts.LibvirtXMLNotFoundError("Attribute %s not found"
                                                     "on element %s"
                                                     % (self.attribute,
                                                        element.tag))
            return value

    class Setter(AccessorBase):

        """
        Set attribute value
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name', 'attribute')

        def __call__(self, value):
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=True)
            element.set(self.attribute, str(value))
            self.xmltreefile().write()

    class Delter(AccessorBase):

        """
        Remove attribute
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name', 'attribute')

        def __call__(self):
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=False)
            try:
                del element.attrib[self.attribute]
            except KeyError:
                pass  # already doesn't exist
            self.xmltreefile().write()


class XMLElementDict(AccessorGeneratorBase):

    """
    Class of accessor classes operating as a dictionary of attributes
    """

    def __init__(self, property_name, libvirtxml, forbidden=None,
                 parent_xpath=None, tag_name=None):
        """
        Create undefined accessors on libvirt instance

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param forbidden: Optional list of 'Getter', 'Setter', 'Delter'
        :param parent_xpath: XPath string of parent element
        :param tag_name: element tag name to manipulate text attribute on.
        """
        super(XMLElementDict, self).__init__(property_name, libvirtxml,
                                             forbidden,
                                             parent_xpath=parent_xpath,
                                             tag_name=tag_name)

    class Getter(AccessorBase):

        """
        Retrieve attributes on element
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name')

        def __call__(self):
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=False)
            return dict(element.items())

    class Setter(AccessorBase):

        """
        Set attributes to value on element
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name')

        def __call__(self, value):
            type_check(self.property_name + ' value', value, dict)
            element = self.element_by_parent(self.parent_xpath,
                                             self.tag_name, create=True)
            for attr_key, attr_value in value.items():
                element.set(str(attr_key), str(attr_value))
            self.xmltreefile().write()

    # Inheriting from XMLElementText not work right
    Delter = XMLElementText.Delter


class XMLElementNest(AccessorGeneratorBase):

    """
    Class of accessor classes operating on a LibvirtXMLBase subclass
    """

    required_dargs = ('parent_xpath', 'tag_name', 'subclass', 'subclass_dargs')

    def __init__(self, property_name, libvirtxml, forbidden=None,
                 parent_xpath=None, tag_name=None, subclass=None,
                 subclass_dargs=None):
        """
        Create undefined accessors on libvirt instance

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param forbidden: Optional list of 'Getter', 'Setter', 'Delter'
        :param parent_xpath: XPath string of parent element
        :param tag_name: element tag name to manipulate text attribute on.
        :param subclass: A LibvirtXMLBase subclass with root tag == tag_name
        :param subclass_dargs: dict. to pass as kw args to subclass.__init__

        N/B: Works ONLY if tag_name is unique within parent element
        """
        type_check('subclass', subclass, base.LibvirtXMLBase)
        type_check('subclass_dargs', subclass_dargs, dict)
        super(XMLElementNest, self).__init__(property_name, libvirtxml,
                                             forbidden,
                                             parent_xpath=parent_xpath,
                                             tag_name=tag_name,
                                             subclass=subclass,
                                             subclass_dargs=subclass_dargs)

    class Getter(AccessorBase):

        """
        Retrieve instance of subclass with it's xml set to rerooted xpath/tag
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name', 'subclass',
                                 'subclass_dargs')

        def __call__(self):
            xmltreefile = self.xmltreefile()
            # Don't re-invent XPath generation method/behavior
            nested_root_element = self.element_by_parent(self.parent_xpath,
                                                         self.tag_name,
                                                         create=False)
            nested_root_xpath = xmltreefile.get_xpath(nested_root_element)
            # Try to make XMLTreeFile copy, rooted at nested_root_xpath
            # with copies of any/all child elements also
            nested_xtf = xmltreefile.reroot(nested_root_xpath)
            # Create instance of subclass to assign nested_xtf onto
            nestedinst = self.subclass(**self.subclass_dargs)
            # nestedxml.xmltreefile.restore() will fail on nested_xtf.__del__
            nestedinst.set_xml(str(nested_xtf))  # set from string not filename!
            return nestedinst

    class Setter(AccessorBase):

        """
        Set attributes to value on element
        """

        __slots__ = add_to_slots('parent_xpath', 'tag_name', 'subclass')

        def __call__(self, value):
            type_check('Instance of %s' % self.subclass.__name__,
                       value,
                       self.subclass)
            # Will overwrite if exists
            existing_element = self.element_by_parent(self.parent_xpath,
                                                      self.tag_name,
                                                      create=True)
            existing_parent = self.xmltreefile().get_parent(existing_element)
            self.xmltreefile().remove(existing_element)
            existing_parent.append(value.xmltreefile.getroot())
            self.xmltreefile().write()

    # Nothing fancy, just make sure that part of tree doesn't exist
    Delter = XMLElementText.Delter


class XMLElementList(AccessorGeneratorBase):

    """
    Class of accessor classes operating on a list of child elements

    Other generators here have a hard-time dealing with XML that has
    multiple child-elements with the same tag.  This class allows
    treating these structures as lists of arbitrary user-defined
    objects.  User-defined marshal functions are called to perform
    the conversion to/from the format described in __init__.
    """

    required_dargs = ('parent_xpath', 'tag_name', 'marshal_from', 'marshal_to')

    def __init__(self, property_name, libvirtxml, forbidden=None,
                 parent_xpath=None, marshal_from=None, marshal_to=None):
        """
        Create undefined accessors on libvirt instance

        :param property_name: String name of property (for exception detail)
        :param libvirtxml: An instance of a LibvirtXMLBase subclass
        :param forbidden: Optional list of 'Getter', 'Setter', 'Delter'
        :param parent_xpath: XPath string of parent element
        :param marshal_from: Callable, passed the item, index, and
                              libvirtxml instance.  Must return tuple
                              of tag-name, and an attribute-dict or raise
                              ValueError exception.
        :param marshal_to: Callable. Passed a the item tag, attribute-dict.,
                            index, and libvirtxml instance.  Returns
                            item value accepted by marshal_from or None to skip
        """
        if not callable(marshal_from) or not callable(marshal_to):
            raise ValueError("Both marshal_from and marshal_to must be "
                             "callable")
        super(XMLElementList, self).__init__(property_name, libvirtxml,
                                             forbidden,
                                             parent_xpath=parent_xpath,
                                             marshal_from=marshal_from,
                                             marshal_to=marshal_to)

    class Getter(AccessorBase):

        """
        Retrieve list of values as returned by the marshal_to callable
        """

        __slots__ = add_to_slots('parent_xpath', 'marshal_to')

        def __call__(self):
            # Parent structure cannot be pre-determined as in other classes
            parent = self.xmltreefile().find(self.parent_xpath)
            if parent is None:
                # Used as "undefined" signal, raising exception may
                # not be appropriate when other accessors are used
                # to generate missing structure.
                return None
            result = []
            # Give user-defined marshal functions a way to act on
            # item order if needed, and/or help with error reporting.
            index = 0
            # user-defined marshal functions might want to use
            # index numbers to filter/skip certain elements
            # but also support specific item ordering.
            for child in parent.getchildren():
                # Call user-defined helper to translate Element
                # into simple pre-defined format.
                item = self.marshal_to(child.tag, dict(child.items()),
                                       index, self.libvirtxml)
                if item is not None:
                    result.append(item)
                # Always use absolute index (even if item was None)
                index += 1
            return result

    class Setter(AccessorBase):

        """
        Set child elements as returned by the marshal_to callable
        """

        __slots__ = add_to_slots('parent_xpath', 'marshal_from')

        def __call__(self, value):
            type_check('value', value, list)
            # Allow other classes to generate parent structure
            parent = self.xmltreefile().find(self.parent_xpath)
            if parent is None:
                raise xcepts.LibvirtXMLNotFoundError
            # Remove existing by calling accessor method, allowing
            # any "untouchable" or "filtered" elements (by marshal)
            # to be ignored and left as-is.
            delattr(self.libvirtxml, self.property_name)
            # Allow user-defined marshal function to determine
            # if item order is important.  Also give more meaningful
            # exception message below, if there is a problem.
            index = 0
            for item in value:
                try:
                    # Call user-defined conversion from simple
                    # format, back to Element instances.
                    element_tuple = self.marshal_from(item, index,
                                                      self.libvirtxml)
                except ValueError:
                    # Defined in marshal API, to help with error reporting
                    # and debugging with more rich message.
                    msg = ("Call to %s by set accessor method for property %s "
                           "with unsupported item type %s, at index %d, "
                           " with value %s." % (str(self.marshal_from),
                                                self.property_name,
                                                str(type(item)),
                                                index,
                                                str(item)))
                    raise xcepts.LibvirtXMLAccessorError(msg)
                xml_utils.ElementTree.SubElement(parent,
                                                 element_tuple[0],
                                                 element_tuple[1])
                index += 1
            self.xmltreefile().write()

    class Delter(AccessorBase):

        """
        Remove ALL child elements for which marshal_to does NOT return None
        """

        __slots__ = add_to_slots('parent_xpath', 'marshal_to')

        def __call__(self):
            parent = self.xmltreefile().find(self.parent_xpath)
            if parent is None:
                raise xcepts.LibvirtXMLNotFoundError("Parent element %s not "
                                                     "found" % self.parent_xpath)
            # Don't delete while traversing list
            todel = []
            index = 0
            for child in parent.getchildren():
                item = self.marshal_to(child.tag, dict(child.items()),
                                       index, self.libvirtxml)
                # Always use absolute index (even if item was None)
                index += 1
                # Account for case where child elements are mixed in
                # with other elements not supported by this class.
                # Also permits marshal functions to do element filtering
                # if the class should only address specificly attributed
                # elements.
                if item is not None:
                    todel.append(child)
            for child in todel:
                parent.remove(child)
