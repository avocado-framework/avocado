# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014
#
# Authors: Ruda Moura <rmoura@redhat.com>
#          Ademar Reis <areis@redhat.com>
#          Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Base classes for implementing the varianter interface
"""

import hashlib

from six import iteritems, itervalues

from . import tree
from . import dispatcher
from . import output
from ..utils import astring


def is_empty_variant(variant):
    """
    Reports whether the variant contains any data

    :param variant: Avocado test variant (list of TreeNode-like objects)
    :return: True when the variant does not contain (any useful) data
    """
    return not variant or variant == [tree.TreeNode()] * len(variant)


def generate_variant_id(variant):
    """
    Basic function to generate variant-id from a variant

    :param variant: Avocado test variant (list of TreeNode-like objects)
    :return: String compounded of ordered node names and a hash of all
             values.
    """
    variant = sorted(variant, key=lambda x: x.path)
    fingerprint = "\n".join(_.fingerprint() for _ in variant)
    return ("-".join(node.name for node in variant) + '-' +
            hashlib.sha1(fingerprint.encode(astring.ENCODING)).hexdigest()[:4])


def variant_to_str(variant, verbosity, out_args=None, debug=False):
    """
    Reports human readable representation of a variant

    :param variant: Valid variant (list of TreeNode-like objects)
    :param verbosity: Output verbosity where 0 means brief
    :param out_args: Extra output arguments (currently unused)
    :param debug: Whether the variant contains and should report debug info
    :return: Human readable representation
    """
    del out_args
    out = []
    if not debug:
        paths = ', '.join([x.path for x in variant["variant"]])
    else:
        color = output.TERM_SUPPORT.LOWLIGHT
        cend = output.TERM_SUPPORT.ENDC
        paths = ', '.join(["%s%s@%s%s" % (_.name, color,
                                          getattr(_, 'yaml',
                                                  "Unknown"),
                                          cend)
                           for _ in variant["variant"]])
    out.append('%sVariant %s:    %s' % ('\n' if verbosity else '',
                                        variant["variant_id"],
                                        paths))
    if verbosity:
        env = set()
        for node in variant["variant"]:
            for key, value in iteritems(node.environment):
                origin = node.environment.origin[key].path
                env.add(("%s:%s" % (origin, key), astring.to_text(value)))
        if not env:
            return out
        fmt = '    %%-%ds => %%s' % max([len(_[0]) for _ in env])
        for record in sorted(env):
            out.append(fmt % record)
    return out


def dump_ivariants(ivariants):
    """
    Walks the iterable variants and dumps them into json-serializable object
    """
    def dump_tree_node(node):
        """
        Turns TreeNode-like object into tuple(path, env_representation)
        """
        return (astring.to_text(node.path),
                [(astring.to_text(node.environment.origin[key].path),
                  astring.to_text(key), value)
                 for key, value in iteritems(node.environment)])

    variants = []
    for variant in ivariants():
        safe_variant = {}
        safe_variant["paths"] = [astring.to_text(pth)
                                 for pth in variant.get("paths")]
        safe_variant["variant_id"] = variant.get("variant_id")
        safe_variant["variant"] = [dump_tree_node(_)
                                   for _ in variant.get("variant", [])]
        variants.append(safe_variant)
    return variants


class FakeVariantDispatcher(object):

    """
    This object can act instead of VarianterDispatcher to report loaded
    variants.
    """

    def __init__(self, state):
        for variant in state:
            variant["variant"] = [tree.TreeNodeEnvOnly(path, env)
                                  for path, env in variant["variant"]]
        self.variants = state

    def map_method(self, method, *args, **kwargs):
        """
        Reports list containing one result of map_method on self
        """
        if hasattr(self, method):
            return [getattr(self, method)(*args, **kwargs)]
        else:
            return []

    def to_str(self, summary=0, variants=0, **kwargs):  # pylint: disable=W0613
        if not self.variants:
            return ""
        out = []
        for variant in self.variants:
            paths = ', '.join([x.path for x in variant["variant"]])
            out.append('\nVariant %s:    %s' % (variant["variant_id"],
                                                paths))
            env = set()
            for node in variant["variant"]:
                for key, value in iteritems(node.environment):
                    origin = node.environment.origin[key].path
                    env.add(("%s:%s" % (origin, key), astring.to_text(value)))
            if not env:
                continue
            fmt = '    %%-%ds => %%s' % max([len(_[0]) for _ in env])
            for record in sorted(env):
                out.append(fmt % record)
        return "\n".join(out)

    def __iter__(self):
        return iter(self.variants)

    def __len__(self):
        return sum(1 for _ in self)


class Varianter(object):

    """
    This object takes care of producing test variants
    """

    def __init__(self, debug=False, state=None):
        """
        :param debug: Store whether this instance should debug varianter
        :param state: Force-varianter state
        :note: it's necessary to check whether variants debug is enable
               in order to provide the right results.
        """
        self.default_params = {}
        self._default_params = None
        if state is None:
            self.debug = debug
            self.node_class = tree.TreeNodeDebug if debug else tree.TreeNode
            self._variant_plugins = dispatcher.VarianterDispatcher()
            self._no_variants = None
        else:
            self.load(state)

    def parse(self, args):
        """
        Apply options defined on the cmdline and initialize the plugins.

        :param args: Parsed cmdline arguments
        """
        default_params = self.node_class()
        for default_param in itervalues(self.default_params):
            default_params.merge(default_param)
        self._default_params = default_params
        self.default_params.clear()
        self._variant_plugins.map_method("initialize", args)
        self._variant_plugins.map_method_copy("update_defaults", self._default_params)
        self._no_variants = sum(self._variant_plugins.map_method("__len__"))

    def is_parsed(self):
        """
        Reports whether the varianter was already parsed
        """
        return self._no_variants is not None

    def add_default_param(self, name, key, value, path=None):   # pylint: disable=E0202
        """
        Stores the path/key/value into default params

        This allow injecting default arguments which are mainly intended for
        machine/os-related params. It should not affect the test results
        and by definition it should not affect the variant id.

        :param name: Name of the component which injects this param
        :param key: Key to which we'd like to assign the value
        :param value: The key's value
        :param path: Optional path to the node to which we assign the value,
                     by default '/'.
        """
        if path is None:
            path = "/"
        if name not in self.default_params:
            self.default_params[name] = self.node_class()
        self.default_params[name].get_node(path, True).value[key] = value

    def to_str(self, summary=0, variants=0, **kwargs):
        """
        Return human readable representation

        The summary/variants accepts verbosity where 0 means do not display
        at all and maximum is up to the plugin.

        :param summary: How verbose summary to output (int)
        :param variants: How verbose list of variants to output (int)
        :param kwargs: Other free-form arguments
        :rtype: str
        """
        if self._no_variants == 0:  # No variants, only defaults:
            out = []
            if summary:
                out.append("No variants available, using defaults only")
            if variants:
                variant = next(self.itertests())
                variant["variant_id"] = ""  # Don't confuse people with None
                out.append("\n".join(variant_to_str(variant, variants - 1,
                                                    kwargs, self.debug)))
            return "\n\n".join(out)

        out = [item for item in self._variant_plugins.map_method("to_str",
                                                                 summary,
                                                                 variants,
                                                                 **kwargs)
               if item]

        return "\n\n".join(out)

    def get_number_of_tests(self, test_suite):
        """
        :return: overall number of tests * number of variants
        """
        # Currently number of tests is symmetrical
        if self._no_variants:
            return len(test_suite) * self._no_variants
        else:
            return len(test_suite)

    def dump(self):
        """
        Dump the variants in loadable-state

        This is lossy representation which takes all yielded variants and
        replaces the list of nodes with TreeNodeEnvOnly representations::

            [{'path': path,
              'variant_id': variant_id,
              'variant': dump_tree_nodes(original_variant)},
             {'path': [str, str, ...],
              'variant_id': str,
              'variant': [(str, [(str, str, object), ...])],
             {'path': ['/run/*'],
              'variant_id': 'cat-26c0'
              'variant': [('/pig/cat',
                           [('/pig', 'ant', 'fox'),
                            ('/pig/cat', 'dog', 'bee')])]}
             ...]

        where `dump_tree_nodes` looks like::

            [(node.path, environment_representation),
             (node.path, [(path1, key1, value1), (path2, key2, value2), ...]),
             ('/pig/cat', [('/pig', 'ant', 'fox')])

        :return: loadable Varianter representation
        """
        if not self.is_parsed():
            raise NotImplementedError("Dumping Varianter state before "
                                      "multiplexation is not supported.")
        return dump_ivariants(self.itertests)

    def load(self, state):
        """
        Load the variants state

        Current implementation supports loading from a list of loadable
        variants. It replaces the VariantDispatcher with fake implementation
        which reports the loaded (and initialized) variants.

        :param state: loadable Varianter representation
        """
        # TODO: Remove when 52.0 is deprecated
        # In 52.0 the "paths" was called "mux_path"
        for variant in state:
            if "mux_path" in variant and "paths" not in variant:
                variant["paths"] = variant["mux_path"]
        self.debug = False
        self.node_class = tree.TreeNode
        self._variant_plugins = FakeVariantDispatcher(state)
        self._no_variants = sum(self._variant_plugins.map_method("__len__"))

    def itertests(self):
        """
        Yields all variants of all plugins

        The variant is defined as dictionary with at least:
         * variant_id - name of the current variant
         * variant - AvocadoParams-compatible variant (usually a list of
                     TreeNodes but dict or simply None are also possible
                     values)
         * paths - default path(s)

        :yield variant
        """
        if self._no_variants:  # Copy template and modify it's params
            plugins_variants = self._variant_plugins.map_method("__iter__")
            iter_variants = (variant
                             for plugin_variants in plugins_variants
                             for variant in plugin_variants)
            for variant in iter(iter_variants):
                yield variant
        else:   # No variants, use template
            yield {"variant": self._default_params.get_leaves(),
                   "variant_id": None,
                   "paths": ["/run/*"]}

    def __len__(self):
        return self._no_variants
