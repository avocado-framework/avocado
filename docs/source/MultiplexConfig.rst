.. _multiplex_configuration:

=======================
Multiplex Configuration
=======================

Multiplex Configuration is a specialized way of providing lists
of key/value pairs within combination's of various categories,
that will be passed to avocado test as parameters in a dictionary
called ``params``. The format simplifies and condenses complex
multidimensional arrays of test parameters into a flat list. The
combinatorial result can be filtered and adjusted prior to testing.

The parser relies on `YAML <http://www.yaml.org/>`_, a human friendly
markup language.  The YAML format allows one to create, manually or
with code automation, multiple configurations for the tests. You can use any
text editor to write YAML files, but choose one that supports syntax
enhancements and basic validation, it saves time!

Here is how a simple and valid multiplex configuration looks like::

    # Multiplex config example, file sleep.yaml
    short:
        sleep_length: 1
    medium:
        sleep_length: 60
    long:
        sleep_length: 600

The key concepts here are ``nodes`` (provides context and scope), ``keys`` (think of variables) and ``values`` (scalar or lists).
In the next section, we will describe these concepts in more details.

.. _nodes:

Nodes
=====

Nodes servers for two purposes, to name or describe a discrete point of information
and to store in a set of key/values (possibly empty). Basically nodes can contains
other nodes, so will have the parent and child relationship in a tree structure.

The tree node structure can be obtained by using the command line
``avocado multiplex --tree <file>`` and for previous example,
it looks just like this::

    avocado multiplex --tree sleep.yaml
    Config file tree structure:

         /-short
        |
    ----|-medium
        |
         \-long

It helps if you see the tree structure as a set of paths
separated by ``/``, much like paths in the file system.

In the example we have being working on, there are only three paths:

- ``//short``
- ``//medium``
- ``//long``

The ending nodes (the leafs on the tree) will become part of all lower-level
(i.e. further indented) variant stanzas (see section variants_).
However, the precedence is evaluated in top-down or ``last defined`` order.
In other words, the last parsed has precedence over earlier definitions.

.. _keys_and_values:

Keys and Values
===============

Keys and values are the most basic useful facility provided by the
format. A statement in the form ``<key>: <value>`` sets ``<key>`` to
``<value>``.

Values are numbers, strings and lists. Some examples of literal values:

- Booleans: ``true`` and ``false``.
- Numbers: 123 (integer), 3.1415 (float point)
- Strings: 'This is a string'

And lists::

    cflags:
        - '-O2'
        - '-g'
        - '-Wall'

The list above will become ``['-O2', '-g', '-Wall']`` to Python. In fact,
YAML is compatible to JSON.
.. _environment:

Environment
===========

The environment is a set of key/values constructed by the moment
we walk the path (beginning from the root) until we reach a specific node.

Given the node structure bellow::

    devtools:
        compiler: 'cc'
        flags:
            - '-O2'
        debug: '-g'
        fedora:
            compiler: 'gcc'
            flags:
                - '-Wall'
        osx:
            compiler: 'clang'
            flags:
                - '-arch i386'
                - '-arch x86_64'

And the rules defined as:

* Scalar values (Booleans, Numbers and Strings) are overwritten by walking from the root until the final node.
* Lists are appended (to the tail) whenever we walk from the root to the final node.

The environment created for the nodes ``fedora`` and ``osx`` are:

- Node ``//devtools/fedora`` environment ``compiler: 'gcc'``, ``flags: ['-O2', '-Wall']``
- None ``//devtools/osx`` environment ``compiler: 'clang'``, ``flags: ['-O2', '-arch i386', '-arch x86_64']``

.. _variants:

Variants
========

To be written.

Avocado comes equipped with a plugin to parse multiplex files. The appropriate
subcommand is::

    avocado multiplex /path/to/multiplex.yaml [-c]

Note that there's no need to put extensions to a multiplex file, although
doing so helps with organization. The optional -c param is used to provide
the contents of the dictionaries generated, not only their shortnames.

``avocado multiplex`` against the content above produces the following
combinations and names::

    Dictionaries generated:
        dict 1:    four.one
        dict 2:    four.two
        dict 3:    four.three
        dict 4:    five.one
        dict 5:    five.two
        dict 6:    five.three
        dict 7:    six.one
        dict 8:    six.two
        dict 9:    six.three

With Nodes, Keys, Values & Filters, we have most of what you
actually need to construct most multiplex files.
