"""
Debug version of the avocado.core.tree.TreeNode with additional utils.
:license: GPLv2
:copyright: Red Hat, Inc. 2014
:author: Lukas Doktor <ldoktor@redhat.com>
"""

import itertools
import os

from avocado.core import output
from avocado.core.tree import TreeNode


class OutputValue(object):  # only container pylint: disable=R0903

    """ Ordinary value with some debug info """

    def __init__(self, value, node, srcyaml):
        self.value = value
        self.node = node
        self.yaml = srcyaml

    def __str__(self):
        return "%s%s@%s:%s%s" % (self.value,
                                 output.term_support.LOWLIGHT,
                                 self.yaml, self.node.path,
                                 output.term_support.ENDC)


class OutputList(list):  # only container pylint: disable=R0903

    """ List with some debug info """

    def __init__(self, values, nodes, yamls):
        super(OutputList, self).__init__(values)
        self.nodes = nodes
        self.yamls = yamls

    def __add__(self, other):
        """ Keep attrs separate in order to print the origins """
        value = super(OutputList, self).__add__(other)
        return OutputList(value,
                          self.nodes + other.nodes,
                          self.yamls + other.yamls)

    def __str__(self):
        color = output.term_support.LOWLIGHT
        cend = output.term_support.ENDC
        return ' + '.join("%s%s@%s:%s%s"
                          % (_[0], color, _[1], _[2].path, cend)
                          for _ in itertools.izip(self, self.yamls,
                                                  self.nodes))


class ValueDict(dict):  # only container pylint: disable=R0903

    """ Dict which stores the origin of the items """

    def __init__(self, srcyaml, node, values):
        super(ValueDict, self).__init__()
        self.yaml = srcyaml
        self.node = node
        self.yaml_per_key = {}
        for key, value in values.iteritems():
            self[key] = value

    def __setitem__(self, key, value):
        """ Store yaml_per_key and value """
        # Merge is responsible to set `self.yaml` to current file
        self.yaml_per_key[key] = self.yaml
        return super(ValueDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        """
        This is debug run. Fake the results and return either
        OutputValue (let's call it string) and OutputList. These
        overrides the `__str__` and return string with origin.
        :warning: Returned values are unusable in tests!
        """
        value = super(ValueDict, self).__getitem__(key)
        origin = self.yaml_per_key.get(key)
        if isinstance(value, list):
            value = OutputList([value], [self.node], [origin])
        else:
            value = OutputValue(value, self.node, origin)
        return value

    def iteritems(self):
        """ Slower implementation with the use of __getitem__ """
        for key in self.iterkeys():
            yield key, self[key]
        raise StopIteration


class TreeNodeDebug(TreeNode):  # only container pylint: disable=R0903

    """
    Debug version of TreeNodeDebug
    :warning: Origin of the value is appended to all values thus it's not
    suitable for running tests.
    """

    def __init__(self, name='', value=None, parent=None, children=None,
                 srcyaml=None):
        if value is None:
            value = {}
        if srcyaml:
            srcyaml = os.path.relpath(srcyaml)
        super(TreeNodeDebug, self).__init__(name,
                                            ValueDict(srcyaml, self, value),
                                            parent, children)
        self.yaml = srcyaml

    def merge(self, other):
        """
        Override origin with the one from other tree. Updated/Newly set values
        are going to use this location as origin.
        """
        if hasattr(other, 'yaml'):
            srcyaml = os.path.relpath(other.yaml)
            # when we use TreeNodeDebug, value is always ValueDict
            self.value.yaml_per_key.update(other.value.yaml_per_key)    # pylint: disable=E1101
        else:
            srcyaml = "Unknown"
        self.yaml = srcyaml
        self.value.yaml = srcyaml
        return super(TreeNodeDebug, self).merge(other)


def get_named_tree_cls(path):
    """ Return TreeNodeDebug class with hardcoded yaml path """
    class NamedTreeNodeDebug(TreeNodeDebug):    # pylint: disable=R0903

        """ Fake class with hardcoded yaml path """

        def __init__(self, name='', value=None, parent=None,
                     children=None):
            super(NamedTreeNodeDebug, self).__init__(name, value, parent,
                                                     children, path)
    return NamedTreeNodeDebug
