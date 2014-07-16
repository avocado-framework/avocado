"""
    Utility module standardized on ElementTree 2.6 to minimize dependencies
    in python 2.4 systems.

    Often operations on XML files suggest making a backup copy first is a
    prudent measure.  However, it's easy to loose track of these temporary
    files and they can quickly leave a mess behind.  The TempXMLFile class
    helps by trying to clean up the temporary file whenever the instance is
    deleted, goes out of scope, or an exception is thrown.

    The XMLBackup class extends the TempXMLFile class by basing its file-
    like instances off of an automatically created TempXMLFile instead of
    pointing at the source.  Methods are provided for overwriting the backup
    copy from the source, or restoring the source from the backup.  Similar
    to TempXMLFile, the temporary backup files are automatically removed.
    Access to the original source is provided by the sourcefilename
    attribute.

    An interface for querying and manipulating XML data is provided by
    the XMLTreeFile class.  Instances of this class are BOTH file-like
    and ElementTree-like objects.  Whether or not they are constructed
    from a file or a string, the file-like instance always represents a
    temporary backup copy.  Access to the source (even when itself is
    temporary) is provided by the sourcefilename attribute, and a (closed)
    file object attribute sourcebackupfile.  See the ElementTree documentation
    for methods provided by that class.

    Finally, the TemplateXML class represents XML templates that support
    dynamic keyword substitution based on a dictionary.  Substitution keys
    in the XML template (string or file) follow the 'bash' variable reference
    style ($foo or ${bar}).  Extension of the parser is possible by subclassing
    TemplateXML and overriding the ParserClass class attribute.  The parser
    class should be an ElementTree.TreeBuilder class or subclass.  Instances
    of XMLTreeFile are returned by the parse method, which are themselves
    temporary backups of the parsed content.  See the xml_utils_unittest
    module for examples.
"""

import os
import shutil
import tempfile
import string
import StringIO
import logging
from xml.parsers import expat
# We *have* to use our ElementTree fork :(
from virttest import element_tree as ElementTree

# Also used by unittests
TMPPFX = 'xml_utils_temp_'
TMPSFX = '.xml'
EXSFX = '_exception_retained'
ENCODING = "UTF-8"


class TempXMLFile(file):

    """
    Temporary XML file auto-removed on instance del / module exit.
    """

    def __init__(self, suffix=TMPSFX, prefix=TMPPFX, mode="wb+", buffsz=1):
        """
        Initialize temporary XML file removed on instance destruction.

        param: suffix: temporary file's suffix
        param: prefix: temporary file's prefix
        param: mode: second parameter to file()/open()
        param: buffer: third parameter to file()/open()
        """
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        os.close(fd)
        super(TempXMLFile, self).__init__(path, mode, buffsz)

    def _info(self):
        """
        Inform user that file was not auto-deleted due to exceptional exit.
        """
        logging.info("Retaining %s", self.name + EXSFX)

    def unlink(self):
        """
        Unconditionaly delete file, ignoring related exceptions
        """
        try:
            os.unlink(self.name)
            self.close()
        except (OSError, IOError):
            pass  # don't care if delete fails

    def __exit__(self, exc_type, exc_value, traceback):
        """
        unlink temporary backup on unexceptional module exit.
        """

        # there was an exception
        if None not in (exc_type, exc_value, traceback):
            os.rename(self.name, self.name + EXSFX)
        else:
            self.unlink()  # safe if file was renamed
        if hasattr(super(TempXMLFile, self), '__exit__'):
            super(TempXMLFile, self).__exit__(exc_type, exc_value, traceback)

    def __del__(self):
        """
        unlink temporary file on instance delete.
        """
        self.close()
        self.unlink()


class XMLBackup(TempXMLFile):

    """
    Backup file copy of XML data, automatically removed on instance destruction.
    """

    # Allow users to reference original source of XML data
    sourcefilename = None

    def __init__(self, sourcefilename):
        """
        Initialize a temporary backup from sourcefilename.
        """

        super(XMLBackup, self).__init__()
        self.sourcefilename = sourcefilename
        XMLBackup.backup(self)

    def __del__(self):
        # Drop reference, don't delete source!
        self.sourcefilename = None
        super(XMLBackup, self).__del__()

    def _info(self):
        """
        Inform user that file was not auto-deleted due to exceptional exit.
        """
        logging.info("Retaining backup of %s in %s", self.sourcefilename,
                     self.name + EXSFX)

    def backup(self):
        """
        Overwrite temporary backup with contents of original source.
        """
        super(XMLBackup, self).flush()
        super(XMLBackup, self).seek(0)
        super(XMLBackup, self).truncate(0)
        source_file = file(self.sourcefilename, "rb")
        shutil.copyfileobj(source_file,
                           super(XMLBackup, self))
        source_file.close()
        super(XMLBackup, self).flush()

    def restore(self):
        """
        Overwrite original source with contents of temporary backup
        """
        super(XMLBackup, self).flush()
        super(XMLBackup, self).seek(0)
        source_file = file(self.sourcefilename, "wb")
        source_file.truncate(0)
        shutil.copyfileobj(super(XMLBackup, self),
                           source_file)
        source_file.close()


class XMLTreeFile(ElementTree.ElementTree, XMLBackup):

    """
    Combination of ElementTree root and auto-cleaned XML backup file.
    """

    # Closed file object of original source or TempXMLFile
    # self.sourcefilename inherited from parent
    sourcebackupfile = None

    def __init__(self, xml):
        """
        Initialize from a string or filename containing XML source.

        param: xml: A filename or string containing XML
        """

        # xml param could be xml string or readable filename
        # If it's a string, use auto-delete TempXMLFile
        # to hold the original content.
        try:
            # Test if xml is a valid filename
            self.sourcebackupfile = file(xml, "rb")
            self.sourcebackupfile.close()
            # XMLBackup init will take care of creating a copy
        except (IOError, OSError):
            # Assume xml is a string that needs a temporary source file
            self.sourcebackupfile = TempXMLFile()
            self.sourcebackupfile.write(xml)
            self.sourcebackupfile.close()
        # sourcebackupfile now safe to use for base class initialization
        XMLBackup.__init__(self, self.sourcebackupfile.name)
        try:
            ElementTree.ElementTree.__init__(self, element=None,
                                             file=self.name)
        except expat.ExpatError:
            raise IOError("Error parsing XML: '%s'" % xml)
        # Required for TemplateXML class to work
        self.write()
        self.flush()  # make sure it's on-disk

    def __str__(self):
        self.write()
        self.flush()
        xmlstr = StringIO.StringIO()
        self.write(xmlstr)
        return xmlstr.getvalue()

    def backup(self):
        """Overwrite original source from current tree"""
        self.write()
        self.flush()
        # self is the 'original', so backup/restore logic is reversed
        super(XMLTreeFile, self).restore()

    def restore(self):
        """Overwrite and reparse current tree from original source"""
        # self is the 'original', so backup/restore logic is reversed
        super(XMLTreeFile, self).backup()
        try:
            ElementTree.ElementTree.__init__(self, element=None,
                                             file=self.name)
        except expat.ExpatError:
            raise IOError("Original XML is corrupt: '%s'"
                          % self.sourcebackupfile.name)

    def backup_copy(self):
        """Return a copy of instance, including copies of files"""
        return self.__class__(self.name)

    def reroot(self, xpath):
        """
        Return a copy of instance, re-rooted onto xpath
        """
        rerooted = self.backup_copy()
        element = rerooted.find(xpath)
        if element is None:
            del rerooted  # cleanup files
            raise KeyError("No element found at %s" % xpath)
        rerooted._setroot(element)
        return rerooted

    def get_parent_map(self, element=None):
        """
        Return a child to parent mapping dictionary

        param: element: Search only below this element
        """
        d = {}
        for p in self.getiterator(element):
            for c in p:
                d[c] = p
        return d

    def get_parent(self, element, relative_root=None):
        """
        Return the parent node of an element or None

        param: element: Element to retrieve parent of
        param: relative_root: Search only below this element
        """
        try:
            return self.get_parent_map(relative_root)[element]
        except KeyError:
            return None

    def get_xpath(self, element):
        """Return the XPath string formed from first-match tag names"""
        parent_map = self.get_parent_map()
        root = self.getroot()
        assert root in parent_map.values()
        if element == root:
            return '.'
        # List of strings reversed at end
        path_list = []
        while element != root:
            # 2.7+ ElementPath supports predicates, so:
            # element_index = list(parent_map[element]).index(element)
            # element_index += 1 # XPath indexes are 1 based
            # if element_index > 1:
            #     path_list.append(u"%s[%d]" % (element.tag, element_index))
            # else:
            #     path_list.append(u"%s" % element.tag)
            path_list.append(u"%s" % element.tag)
            element = parent_map[element]
        assert element == root
        path_list.reverse()
        return "/".join(path_list)

    def remove(self, element):
        """
        Removes a matching subelement.

        :param element: element to be removed.
        """
        self.get_parent(element).remove(element)

    def remove_by_xpath(self, xpath):
        """
        Remove an element found by xpath

        :param xpath: element name or path to remove
        """
        self.remove(self.find(xpath))  # can't remove root

    def create_by_xpath(self, xpath):
        """
        Creates all elements in simplistic xpath from root if not exist
        """
        cur_element = self.getroot()
        for tag in xpath.split('/'):
            next_element = cur_element.find(tag)
            if next_element is None:
                next_element = ElementTree.SubElement(cur_element, tag)
            cur_element = next_element

    def get_element_string(self, xpath):
        """
        Returns the string for the element on xpath.
        """
        return ElementTree.tostring(self.find(xpath))

    # This overrides the file.write() method
    def write(self, filename=None, encoding=ENCODING):
        """
        Write current XML tree to filename, or self.name if None.
        """

        if filename is None:
            filename = self.name
        # Avoid calling file.write() by mistake
        ElementTree.ElementTree.write(self, filename, encoding)

    def read(self, xml):
        self.__del__()
        self.__init__(xml)


class Sub(object):

    """String substituter using string.Template"""

    def __init__(self, **mapping):
        """Initialize substitution mapping."""

        self._mapping = mapping

    def substitute(self, text):
        """
        Use string.safe_substitute on text and return the result

        :param text: string to substitute
        """

        return string.Template(text).safe_substitute(**self._mapping)


class TemplateXMLTreeBuilder(ElementTree.XMLTreeBuilder, Sub):

    """Resolve XML templates into temporary file-backed ElementTrees"""

    BuilderClass = ElementTree.TreeBuilder

    def __init__(self, **mapping):
        """
        Initialize parser that substitutes keys with values in data

        :param **mapping: values to be substituted for ${key} in XML input
        """

        Sub.__init__(self, **mapping)
        ElementTree.XMLTreeBuilder.__init__(self, target=self.BuilderClass())

    def feed(self, data):
        ElementTree.XMLTreeBuilder.feed(self, self.substitute(data))


class TemplateXML(XMLTreeFile):

    """Template-sourced XML ElementTree backed by temporary file."""

    ParserClass = TemplateXMLTreeBuilder

    def __init__(self, xml, **mapping):
        """
        Initialize from a XML string or filename, and string.template mapping.

        :param xml: A filename or string containing XML
        :param **mapping: keys/values to feed with XML to string.template
        """

        self.parser = self.ParserClass(**mapping)
        # ElementTree.init calls self.parse()
        super(TemplateXML, self).__init__(xml)
        # XMLBase.__init__ calls self.write() after super init

    def parse(self, source, parser=None):
        """
        Parse source XML file or filename using TemplateXMLTreeBuilder

        :param source: XML file or filename
        :param parser: ignored
        """
        if parser is None:
            return super(TemplateXML, self).parse(source, self.parser)
        else:
            return super(TemplateXML, self).parse(source, parser)

    def restore(self):
        """
        Raise an IOError to protect the original template source.
        """

        raise IOError("Protecting template source, disallowing restore to %s" %
                      self.sourcefilename)
