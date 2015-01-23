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

It's also possible to remove nodes using python regular
expressions, which can be useful when extending upstream file using downstream
yaml files. This is done by `!remove_node : $value_name` directive::

    os:
        fedora:
        windows:
            3.11:
            95:
    os:
        !remove_node : windows
        windows:
            win3.11:
            win95:

Removes the `windows` node from structure. It's different from `filter-out`
as it really removes the node (and all children) from the tree and
it can be replaced by you new structure as shown in the example. It removes
`windows` with all children and then replaces this structure with slightly
modified version.

As `!remove_node` is processed during merge, when you reverse the order,
windows is not removed and you end-up with `/windows/{win3.11,win95,3.11,95}`
nodes.

Due to yaml nature, it's __mandatory__ to put space between `!remove_node`
and `:`!

Additionally you can prepend multiple nodes to the given node by using
`!using : $prepended/path`. This is useful when extending complex structure,
for example imagine having distro variants in separate ymal files. In the
end you want to merge them into the `/os` node. The main file can be simply::

    # main.yaml
    os:
        !include : os/fedora/21.yaml
        ....

And each file can look either like this::

    # fedora/21.yaml
    fedora:
        21:
            some: value

or you can use `!using` which prepends the `fedora/21`::

    # fedora/21.yaml
    !using : /fedora/21
    some: value

To be precise there is a way to define the structure in the main yaml file::

    # main.yaml
    os:
        fedora:
            21:
                !include : fedora_21.yaml

Or use recursive `!include` (slower)::

    # main.yaml
    os:
        fedora:
            !include : os/fedora.yaml
    # os/fedora.yaml
    21:
        !include : fedora/21.yaml
    # os/fedora/21.yaml
    some: value

Due to yaml nature, it's __mandatory__ to put space between `!using` and `:`!

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

It's also possible to remove key using python's regexp, which can be useful
when extending upstream file using downstream yaml files. This is done by
`!remove_value : $value_name` directive::

    debug:
        CFLAGS: '-O0 -g'
    debug:
        !remove_value: CFLAGS

removes the CFLAGS value completely from the debug node. This happens during
the merge and only once. So if you switch the two, CFLAGS would be defined.

Due to yaml nature, it's __mandatory__ to put space between `!remove_value`
and `:`!

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

.. _multiple_files:

Multiple files
==============

You can provide multiple files. In such scenario final tree is a combination
of the provided files where later nodes with the same name override values of
the precending corresponding node. New nodes are appended as new children::

    file-1.yaml:
        debug:
            CFLAGS: '-O0 -g'
        prod:
            CFLAGS: '-O2'

    file-2.yaml:
        prod:
            CFLAGS: '-Os'
        fast:
            CFLAGS: '-Ofast'

results in::

    debug:
        CFLAGS: '-O0 -g'
    prod:
        CFLAGS: '-Os'       # overriden
    fast:
        CFLAGS: '-Ofast'    # appended

It's also possilbe to include existing file into other file's node. This
is done by `!include : $path` directive::

    os:
        fedora:
            !include : fedora.yaml
        gentoo:
            !include : gentoo.yaml

Due to yaml nature, it's __mandatory__ to put space between `!include` and `:`!

The file location can be either absolute path or relative path to the yaml
file where the `!include` is called (even when it's nested).

Whole file is __merged__ into the node where it's defined.

.. _variants:

Variants
========

When tree parsing and filtering is finished, we create set of variants.
Each variant uses one leaf of each sibling group. For example::

    cpu:
        intel:
        amd:
        arm:
    fmt:
        qcow2:
        raw:

Produces 2 groups `[intel, amd, arm]` and `[qcow2, raw]`, which results in
6 variants (all combinations; product of the groups)

It's also possible to join current node and its children by `!join` tag::

    fmt: !join
        qcow:
            2:
            2v3:
        raw:

Without the join this would produce 2 groups `[2, 2v3]` and `[raw]` resulting
in 2 variants `[2, raw]` and `[2v3, raw]`, which is really not useful.
But we said that `fmt` children should join this sibling group
so it results in one group `[qcow/2, qcow/2v3, raw]` resulting in 3 variants
each of different fmt. This is useful when some
of the variants share some common key. These keys are set inside the
parent, for example here `qcow2.0` and `qcow2.2v3` share the same key
`type: qcow2` and `qcow2.2v3` adds `extra_params` into his params::

    fmt:
        qcow2:
            type: qcow2
            0:
            v3:
                extra_params: "compat=1.1"
        raw:
            type: raw

Complete example::

    hw:
        cpu:
            intel:
            amd:
            arm:
        fmt: !join
            qcow:
                qcow2:
                qcow2v3:
            raw:
    os: !join
        linux: !join
            Fedora:
                19:
            Gentoo:
        windows:
            3.11:

While preserving names and environment values. Then all combinations are
created resulting into 27 unique variants covering all possible combinations
of given tree::

    Variant 1:    /hw/cpu/intel, /hw/fmt/qcow/qcow2, /os/linux/Fedora/19
	Variant 2:    /hw/cpu/intel, /hw/fmt/qcow/qcow2, /os/linux/Gentoo
	Variant 3:    /hw/cpu/intel, /hw/fmt/qcow/qcow2, /os/windows/3.11
	Variant 4:    /hw/cpu/intel, /hw/fmt/qcow/qcow2v3, /os/linux/Fedora/19
	Variant 5:    /hw/cpu/intel, /hw/fmt/qcow/qcow2v3, /os/linux/Gentoo
	Variant 6:    /hw/cpu/intel, /hw/fmt/qcow/qcow2v3, /os/windows/3.11
	Variant 7:    /hw/cpu/intel, /hw/fmt/raw, /os/linux/Fedora/19
	Variant 8:    /hw/cpu/intel, /hw/fmt/raw, /os/linux/Gentoo
	Variant 9:    /hw/cpu/intel, /hw/fmt/raw, /os/windows/3.11
	Variant 10:    /hw/cpu/amd, /hw/fmt/qcow/qcow2, /os/linux/Fedora/19
	Variant 11:    /hw/cpu/amd, /hw/fmt/qcow/qcow2, /os/linux/Gentoo
	Variant 12:    /hw/cpu/amd, /hw/fmt/qcow/qcow2, /os/windows/3.11
	Variant 13:    /hw/cpu/amd, /hw/fmt/qcow/qcow2v3, /os/linux/Fedora/19
	Variant 14:    /hw/cpu/amd, /hw/fmt/qcow/qcow2v3, /os/linux/Gentoo
	Variant 15:    /hw/cpu/amd, /hw/fmt/qcow/qcow2v3, /os/windows/3.11
	Variant 16:    /hw/cpu/amd, /hw/fmt/raw, /os/linux/Fedora/19
	Variant 17:    /hw/cpu/amd, /hw/fmt/raw, /os/linux/Gentoo
	Variant 18:    /hw/cpu/amd, /hw/fmt/raw, /os/windows/3.11
	Variant 19:    /hw/cpu/arm, /hw/fmt/qcow/qcow2, /os/linux/Fedora/19
	Variant 20:    /hw/cpu/arm, /hw/fmt/qcow/qcow2, /os/linux/Gentoo
	Variant 21:    /hw/cpu/arm, /hw/fmt/qcow/qcow2, /os/windows/3.11
	Variant 22:    /hw/cpu/arm, /hw/fmt/qcow/qcow2v3, /os/linux/Fedora/19
	Variant 23:    /hw/cpu/arm, /hw/fmt/qcow/qcow2v3, /os/linux/Gentoo
	Variant 24:    /hw/cpu/arm, /hw/fmt/qcow/qcow2v3, /os/windows/3.11
	Variant 25:    /hw/cpu/arm, /hw/fmt/raw, /os/linux/Fedora/19
	Variant 26:    /hw/cpu/arm, /hw/fmt/raw, /os/linux/Gentoo
	Variant 27:    /hw/cpu/arm, /hw/fmt/raw, /os/windows/3.11

You can generate this list yourself by executing::

    avocado multiplex /path/to/multiplex.yaml [-c]

Note that there's no need to put extensions to a multiplex file, although
doing so helps with organization. The optional -c param is used to provide
the contents of the dictionaries generated, not only their shortnames.

With Nodes, Keys, Values & Filters, we have most of what you
actually need to construct most multiplex files.
