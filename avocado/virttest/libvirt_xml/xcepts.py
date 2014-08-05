"""
Module of common exceptions used in libvirt_xml package
"""


class LibvirtXMLError(Exception):

    """
    Error originating within libvirt_xml module
    """

    def __init__(self, details=''):
        self.details = details
        Exception.__init__(self)

    def __str__(self):
        return str(self.details)


class LibvirtXMLAccessorError(LibvirtXMLError):

    """
    LibvirtXMLError related to an accessor generator class/method
    """
    pass


class LibvirtXMLForbiddenError(LibvirtXMLError):

    """
    LibvirtXMLError raised when operating on a property is prohibited
    """
    pass


class LibvirtXMLNotFoundError(LibvirtXMLError):

    """
    LibvirtXMLError related when an element cannot be found
    """
    pass
