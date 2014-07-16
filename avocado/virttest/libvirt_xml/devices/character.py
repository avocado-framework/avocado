"""
Generic character device support for serial, parallel, channel, and console

http://libvirt.org/formatdomain.html#elementCharSerial
"""

from virttest.libvirt_xml.devices import base


class CharacterBase(base.TypedDeviceBase):

    __slots__ = ('sources', 'targets')

    # Not overriding __init__ because ABC cannot hide device_tag as expected

    # Accessors just wrap private helpers in UntypedDeviceBase class
    def get_sources(self):
        """
        Return a list of dictionaries containing each source's attributes.
        """
        return self._get_list('source')

    def set_sources(self, value):
        """
        Set all sources to the value list of dictionaries of source attributes.
        """
        self._set_list('source', value)

    def del_sources(self):
        """
        Remove the list of dictionaries containing each source's attributes.
        """
        self._del_list('source')

    def get_targets(self):
        """
        Return a list of dictionaries containing each target's attributes.
        """
        return self._get_list('target')

    def set_targets(self, value):
        """
        Set all sources to the value list of dictionaries of target attributes.
        """
        self._set_list('target', value)

    def del_targets(self):
        """
        Remove the list of dictionaries containing each target's attributes.
        """
        self._del_list('target')

    # Some convenience methods so appending to sources/targets is easier
    def add_source(self, **attributes):
        """
        Convenience method for appending a source from dictionary of attributes
        """
        self._add_item('sources', **attributes)

    def add_target(self, **attributes):
        """
        Convenience method for appending a target from dictionary of attributes
        """
        self._add_item('targets', **attributes)

    def update_source(self, index, **attributes):
        """
        Convenience method for merging values into a source's attributes
        """
        self._update_item('sources', index, **attributes)

    def update_target(self, index, **attributes):
        """
        Convenience method for merging values into a target's attributes
        """
        self._update_item('targets', index, **attributes)
