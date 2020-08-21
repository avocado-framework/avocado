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
import json
import os

from ..utils import astring
from . import dispatcher, output, tree

VARIANTS_FILENAME = 'variants.json'


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
    def get_variant_name(variant):
        """
        To get the variant full name string

        :param variant: Avocado test variant (list of TreeNode-like objects)
        :return: Complete variant name string
        """
        full_name = []
        for node in variant:
            var_str = []
            while node:
                var_str.append(node.name)
                node = node.parent if hasattr(node, 'parent') else None
            try:
                # Let's drop repeated node names and empty string
                full_name.extend([x for x in var_str[::-1][1:] if x not in full_name])
            except IndexError:
                pass
        return "-".join(full_name)

    variant = sorted(variant, key=lambda x: x.path)
    fingerprint = "\n".join(_.fingerprint() for _ in variant)
    return (get_variant_name(variant) + '-' +
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
            for key, value in node.environment.items():
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
                 for key, value in node.environment.items()])

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


class FakeVariantDispatcher:

    """
    This object can act instead of VarianterDispatcher to report loaded
    variants.
    """

    def __init__(self, state):
        for variant in state:
            variant["variant"] = [tree.TreeNodeEnvOnly(path, env)
                                  for path, env in variant["variant"]]
        self.variants = state

    def map_method_with_return(self, method, *args, **kwargs):
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
                for key, value in node.environment.items():
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


class Varianter:

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
        if state is None:
            self.debug = debug
            self.node_class = tree.TreeNodeDebug if debug else tree.TreeNode
            self._variant_plugins = dispatcher.VarianterDispatcher()
            self._no_variants = None
        else:
            self.load(state)

    def parse(self, config):
        """
        Apply options defined on the cmdline and initialize the plugins.

        :param config: Configuration received from configuration files, command
                       line parser, etc.
        :type config: dict
        """
        self._variant_plugins.map_method_with_return("initialize", config)
        self._no_variants = sum(self._variant_plugins.map_method_with_return("__len__"))

    def is_parsed(self):
        """
        Reports whether the varianter was already parsed
        """
        return self._no_variants is not None

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
        if self._no_variants == 0:  # No variants
            return ""

        out = [item for item in self._variant_plugins.map_method_with_return("to_str",
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
        self.debug = False
        self.node_class = tree.TreeNode
        self._variant_plugins = FakeVariantDispatcher(state)
        self._no_variants = sum(self._variant_plugins.map_method_with_return("__len__"))

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
            plugins_variants = self._variant_plugins.map_method_with_return("__iter__")
            iter_variants = (variant
                             for plugin_variants in plugins_variants
                             for variant in plugin_variants)
            for variant in iter(iter_variants):
                yield variant
        else:   # No real variants, but currently *something* needs to be returned
            yield {"variant": self.node_class('').get_leaves(),
                   "variant_id": None,
                   "paths": ["/run/*"]}

    @classmethod
    def from_resultsdir(cls, resultsdir):
        """
        Retrieves the job variants objects from the results directory.

        This will return a list of variants since a Job can have multiple
        suites and the variants is per suite.
        """
        path = os.path.join(resultsdir, 'jobdata', VARIANTS_FILENAME)
        if not os.path.exists(path):
            return None

        variants = []
        with open(path, 'r') as variants_file:
            for variant in json.load(variants_file):
                variants.append(cls(state=variant))
        return variants

    def __len__(self):
        return self._no_variants
