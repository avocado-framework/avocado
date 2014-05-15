.. _multiplex_configuration_advanced:

================================
Multiplex Configuration Advanced
================================

The features discussed in the previous session should be enough to get you going
to do a lot of testing work. If you are planning to do more, then you can check
here for some more features of the format.

Named Variants
==============

Named variants allow assigning a parseable name to a variant set.  This enables
an entire variant set to be used for in filters_.  All output combinations will
inherit the named variant key, along with the specific variant name.  For example::

   variants var1_name:
        - one:
            key1 = Hello
        - two:
            key2 = World
        - three:
   variants var2_name:
        - one:
            key3 = Hello2
        - two:
            key4 = World2
        - three:

Using::

   only (var2_name=one).(var1_name=two)

Results in the following outcome when parsed with ``avocado multiplex [file] -c``::

    Dictionaries generated:
        dict 1:    one.two
            _name_map_file = {'docs.mplx': '(var2_name=one).(var1_name=two)'}
            _short_name_map_file = {'docs.mplx': 'one.two'}
            dep = []
            key2 = World
            key3 = Hello2
            name = (var2_name=one).(var1_name=two)
            shortname = one.two
            var1_name = two
            var2_name = one

Named variants could also be used as normal variables.::

   variants guest_os:
        - fedora:
        - ubuntu:
   variants disk_interface:
        - virtio:
        - hda:

Which then results in the following::

    Dictionaries generated:
        dict 1:    virtio.fedora
            _name_map_file = {'docs.mplx': '(disk_interface=virtio).(guest_os=fedora)'}
            _short_name_map_file = {'docs.mplx': 'virtio.fedora'}
            dep = []
            disk_interface = virtio
            guest_os = fedora
            name = (disk_interface=virtio).(guest_os=fedora)
            shortname = virtio.fedora
        dict 2:    virtio.ubuntu
            _name_map_file = {'docs.mplx': '(disk_interface=virtio).(guest_os=ubuntu)'}
            _short_name_map_file = {'docs.mplx': 'virtio.ubuntu'}
            dep = []
            disk_interface = virtio
            guest_os = ubuntu
            name = (disk_interface=virtio).(guest_os=ubuntu)
            shortname = virtio.ubuntu
        dict 3:    hda.fedora
            _name_map_file = {'docs.mplx': '(disk_interface=hda).(guest_os=fedora)'}
            _short_name_map_file = {'docs.mplx': 'hda.fedora'}
            dep = []
            disk_interface = hda
            guest_os = fedora
            name = (disk_interface=hda).(guest_os=fedora)
            shortname = hda.fedora
        dict 4:    hda.ubuntu
            _name_map_file = {'docs.mplx': '(disk_interface=hda).(guest_os=ubuntu)'}
            _short_name_map_file = {'docs.mplx': 'hda.ubuntu'}
            dep = []
            disk_interface = hda
            guest_os = ubuntu
            name = (disk_interface=hda).(guest_os=ubuntu)
            shortname = hda.ubuntu


.. _key_sub_arrays:

Key Sub Arrays
==============

Parameters for objects like VM's utilize arrays of keys specific to a
particular object instance. In this way, values specific to an object
instance can be addressed. For example, a parameter ``vms`` lists the VM
objects names to instantiate in in the current frame's test. Values
specific to one of the named instances should be prefixed to the name:

::

    vms = vm1 second_vm another_vm
    mem = 128
    mem_vm1 = 512
    mem_second_vm = 1024

The result would be, three virtual machine objects are create. The third
one ``another_vm`` receives the default ``mem`` value of 128. The first two
receive specialized values based on their name.

The order in which these statements are written in a configuration file
is not important; statements addressing a single object always override
statements addressing all objects. Note: This is contrary to the way the
Multiplex Configuration file as a whole is parsed (top-down).

.. _include_statements:

Include Statements
==================

The ``include`` statement is utilized within a Multiplex Configuration
file to better organize related content. When parsing, the contents of
any referenced files will be evaluated as soon as the parser encounters
the ``include`` statement. The order in which files are included is
relevant, and will carry through any key/value substitutions
(see section key_sub_arrays_) as if parsing a complete, flat file.

.. _combinatorial_outcome:

Combinatorial outcome
=====================

The output of parsing a multiplex file will be just the names of the
combinatorial result set items (see short-names, section Variants). However,
the ``--contents`` (short ``-c``) parameter may be specified to examine the output in
more depth. Internally, the key/value data is stored/accessed similar to
a python dictionary instance. With the collection of dictionaries all
being part of a python list-like object. Irrespective of the internals,
running this module from the command-line is an excellent tool for both
reviewing and learning about the Multiplex Configuration format.

In general, each individual combination of the defined variants provides
the parameters for a single test. Testing proceeds in order, through
each result, passing the set of keys and values through to the harness
and test code. When examining Multiplex Configuration files, It's
helpful to consider the earliest key definitions as “defaults”, then
look to the end of the file for other top-level override to those
values. If in doubt of where to define or set a key, placing it at the
top indentation level, at the end of the file, will guarantee it is
used.

.. _formal_definition:

Formal Definition
=================

A list of dictionaries is referred to as a frame. The parser
produces a list of dictionaries (dicts). Each dictionary
contains a set of key-value pairs.

Each dict contains at least three keys: ``name``, ``shortname`` and ``depend``.
The values of name and ``shortname`` are strings, and the value of depend
is a list of strings.

The initial frame contains a single dict, whose ``name`` and ``shortname``
are empty strings, and whose depend is an empty list.

Parsing dict contents
---------------------

The dict parser operates on a frame, referred to as the current frame.

A statement of the form ``<key> = <value>`` sets the value of ``<key>`` to
``<value>`` in all dicts of the current frame. If a dict lacks ``<key>``,
it will be created.

A statement of the form ``<key> += <value>`` appends ``<value>`` to the
value of ``<key>`` in all dicts of the current frame. If a dict lacks
``<key>``, it will be created.

A statement of the form ``<key> <= <value>`` pre-pends ``<value>`` to the
value of ``<key>`` in all dicts of the current frame. If a dict lacks
``<key>``, it will be created.

A statement of the form ``<key> ?= <value>`` sets the value of ``<key>``
to ``<value>``, in all dicts of the current frame, but only if ``<key>``
exists in the dict. The operators ``?+=`` and ``?<=`` are also supported.

A statement of the form ``no <regex>`` removes from the current frame
all dicts whose name field matches ``<regex>``.

A statement of the form ``only <regex>`` removes from the current
frame all dicts whose name field does not match ``<regex>``.

Content exceptions
------------------

Single line exceptions have the format ``<regex>: <key> <operator> <value>``
where ``<operator>`` is any of the operators listed above
(e.g. ``=``, ``+=``, ``?<=``). The statement following the
regular expression ``<regex>`` will apply only to the dicts in
the current frame whose name partially matches ``<regex>`` (i.e.
contains a substring that matches ``<regex>``).

A multi-line exception block is opened by a line of the format
``<regex>:``. The text following this line should be indented. The
statements in a multi-line exception block may be assignment
statements (such as ``<key> = <value>``) or no or only statements.
Nested multi-line exceptions are allowed.

Parsing Variants
----------------

A variants block is opened by a ``variants:`` statement. The indentation
level of the statement places the following set within the outer-most
context-level when nested within other ``variant:`` blocks.  The contents
of the ``variants:`` block must be further indented.

A variant-name may optionally follow the ``variants`` keyword, before
the ``:`` character.  That name will be inherited by and decorate all
block content as the key for each variant contained in it's the
block.

The name of the variants are specified as ``- variant_name:``.
Each name is pre-pended to the name field of each dict of the variant's
frame, along with a separator dot ('.').

The contents of each variant may use the format ``<key> <op> <value>``.
They may also contain further ``variants:`` statements.

If the name of the variant is not preceeded by a ``@`` (i.e.
``-@<variant_name>:``), it is pre-pended to the ``shortname`` field of
each dict of the variant's frame. In other words, if a variant's
name is preceeded by a ``@``, it is omitted from the shortname field.

Each variant in a variants block inherits a copy of the frame in
which the ``variants:`` statement appears. The current frame, which
may be modified by the dict parser, becomes this copy.

The frames of the variants defined in the block are
joined into a single frame.  The contents of frame replace the
contents of the outer containing frame (if there is one).

Filters
-------

Filters can be used in 3 ways:

* ``only <filter>``
* ``no <filter>``
* ``<filter>:``

That last one starts a conditional block, see _filters.

Here ``..`` means ``AND`` and ``.`` means ``IMMEDIATELY-FOLLOWED-BY``. Example::

       qcow2..Fedora.14, RHEL.6..raw..boot, smp2..qcow2..migrate..ide

This means `match all dicts whose names have`
``(qcow2 AND (Fedora IMMEDIATELY-FOLLOWED-BY 14))`` ``OR``
``((RHEL IMMEDIATELY-FOLLOWED-BY 6) AND raw AND boot)`` ``OR``
``(smp2 AND qcow2 AND migrate AND ide)``. Note that::

    qcow2..Fedora.14

is equivalent to::

    Fedora.14..qcow2

But::

    qcow2..Fedora.14

is not equivalent to::

    qcow2..14.Fedora

``ide, scsi`` is equivalent to ``scsi, ide``.

.. _examples_multiplex:

Examples
========

A file with no variants, just assignments::

    key1 = value1
    key2 = value2
    key3 = value3

Results in the following::

    Dictionaries generated:
        dict 1:
            dep = []
            key1 = value1
            key2 = value2
            key3 = value3
            name =
            shortname =

Adding a variants block::

    key1 = value1
    key2 = value2
    key3 = value3

    variants:
        - one:
        - two:
        - three:

Results in the following::

    Dictionaries generated:
        dict 1:    one
            _name_map_file = {'docs.mplx': 'one'}
            _short_name_map_file = {'docs.mplx': 'one'}
            dep = []
            key1 = value1
            key2 = value2
            key3 = value3
            name = one
            shortname = one
        dict 2:    two
            _name_map_file = {'docs.mplx': 'two'}
            _short_name_map_file = {'docs.mplx': 'two'}
            dep = []
            key1 = value1
            key2 = value2
            key3 = value3
            name = two
            shortname = two
        dict 3:    three
            _name_map_file = {'docs.mplx': 'three'}
            _short_name_map_file = {'docs.mplx': 'three'}
            dep = []
            key1 = value1
            key2 = value2
            key3 = value3
            name = three
            shortname = three

Modifying dictionaries inside a variant::

    key1 = value1
    key2 = value2
    key3 = value3

    variants:
        - one:
            key1 = Hello World
            key2 <= some_prefix_
        - two:
            key2 <= another_prefix_
        - three:

Results in the following::

    Dictionaries generated:
        dict 1:    one
            _name_map_file = {'docs.mplx': 'one'}
            _short_name_map_file = {'docs.mplx': 'one'}
            dep = []
            key1 = Hello World
            key2 = some_prefix_value2
            key3 = value3
            name = one
            shortname = one
        dict 2:    two
            _name_map_file = {'docs.mplx': 'two'}
            _short_name_map_file = {'docs.mplx': 'two'}
            dep = []
            key1 = value1
            key2 = another_prefix_value2
            key3 = value3
            name = two
            shortname = two
        dict 3:    three
            _name_map_file = {'docs.mplx': 'three'}
            _short_name_map_file = {'docs.mplx': 'three'}
            dep = []
            key1 = value1
            key2 = value2
            key3 = value3
            name = three
            shortname = three

Adding dependencies::

    key1 = value1
    key2 = value2
    key3 = value3

    variants:
        - one:
            key1 = Hello World
            key2 <= some_prefix_
        - two: one
            key2 <= another_prefix_
        - three: one two

Results in the following::

    Dictionaries generated:
        dict 1:    one
            _name_map_file = {'docs.mplx': 'one'}
            _short_name_map_file = {'docs.mplx': 'one'}
            dep = []
            key1 = Hello World
            key2 = some_prefix_value2
            key3 = value3
            name = one
            shortname = one
        dict 2:    two
            _name_map_file = {'docs.mplx': 'two'}
            _short_name_map_file = {'docs.mplx': 'two'}
            dep = ['one']
            key1 = value1
            key2 = another_prefix_value2
            key3 = value3
            name = two
            shortname = two
        dict 3:    three
            _name_map_file = {'docs.mplx': 'three'}
            _short_name_map_file = {'docs.mplx': 'three'}
            dep = ['one', 'two']
            key1 = value1
            key2 = value2
            key3 = value3
            name = three
            shortname = three

Multiple variant blocks::

    key1 = value1
    key2 = value2
    key3 = value3

    variants:
        - one:
            key1 = Hello World
            key2 <= some_prefix_
        - two: one
            key2 <= another_prefix_
        - three: one two

    variants:
        - A:
        - B:

Results in the following::

    Dictionaries generated:
        dict 1:    A.one
            _name_map_file = {'docs.mplx': 'A.one'}
            _short_name_map_file = {'docs.mplx': 'A.one'}
            dep = []
            key1 = Hello World
            key2 = some_prefix_value2
            key3 = value3
            name = A.one
            shortname = A.one
        dict 2:    A.two
            _name_map_file = {'docs.mplx': 'A.two'}
            _short_name_map_file = {'docs.mplx': 'A.two'}
            dep = ['A.one']
            key1 = value1
            key2 = another_prefix_value2
            key3 = value3
            name = A.two
            shortname = A.two
        dict 3:    A.three
            _name_map_file = {'docs.mplx': 'A.three'}
            _short_name_map_file = {'docs.mplx': 'A.three'}
            dep = ['A.one', 'A.two']
            key1 = value1
            key2 = value2
            key3 = value3
            name = A.three
            shortname = A.three
        dict 4:    B.one
            _name_map_file = {'docs.mplx': 'B.one'}
            _short_name_map_file = {'docs.mplx': 'B.one'}
            dep = []
            key1 = Hello World
            key2 = some_prefix_value2
            key3 = value3
            name = B.one
            shortname = B.one
        dict 5:    B.two
            _name_map_file = {'docs.mplx': 'B.two'}
            _short_name_map_file = {'docs.mplx': 'B.two'}
            dep = ['B.one']
            key1 = value1
            key2 = another_prefix_value2
            key3 = value3
            name = B.two
            shortname = B.two
        dict 6:    B.three
            _name_map_file = {'docs.mplx': 'B.three'}
            _short_name_map_file = {'docs.mplx': 'B.three'}
            dep = ['B.one', 'B.two']
            key1 = value1
            key2 = value2
            key3 = value3
            name = B.three
            shortname = B.three

Filters, ``no`` and ``only``::

    key1 = value1
    key2 = value2
    key3 = value3

    variants:
        - one:
            key1 = Hello World
            key2 <= some_prefix_
        - two: one
            key2 <= another_prefix_
        - three: one two

    variants:
        - A:
            no one
        - B:
            only one,three

Results in the following::

    Dictionaries generated:
        dict 1:    A.two
            _name_map_file = {'docs.mplx': 'A.two'}
            _short_name_map_file = {'docs.mplx': 'A.two'}
            dep = ['A.one']
            key1 = value1
            key2 = another_prefix_value2
            key3 = value3
            name = A.two
            shortname = A.two
        dict 2:    A.three
            _name_map_file = {'docs.mplx': 'A.three'}
            _short_name_map_file = {'docs.mplx': 'A.three'}
            dep = ['A.one', 'A.two']
            key1 = value1
            key2 = value2
            key3 = value3
            name = A.three
            shortname = A.three
        dict 3:    B.one
            _name_map_file = {'docs.mplx': 'B.one'}
            _short_name_map_file = {'docs.mplx': 'B.one'}
            dep = []
            key1 = Hello World
            key2 = some_prefix_value2
            key3 = value3
            name = B.one
            shortname = B.one
        dict 4:    B.three
            _name_map_file = {'docs.mplx': 'B.three'}
            _short_name_map_file = {'docs.mplx': 'B.three'}
            dep = ['B.one', 'B.two']
            key1 = value1
            key2 = value2
            key3 = value3
            name = B.three
            shortname = B.three

Some short names::

    key1 = value1
    key2 = value2
    key3 = value3

    variants:
        - one:
            key1 = Hello World
            key2 <= some_prefix_
        - two: one
            key2 <= another_prefix_
        - three: one two

    variants:
        - @A:
            no one
        - B:
            only one,three

Results in the following::

    Dictionaries generated:
        dict 1:    two
            _name_map_file = {'docs.mplx': 'A.two'}
            _short_name_map_file = {'docs.mplx': 'A.two'}
            dep = ['A.one']
            key1 = value1
            key2 = another_prefix_value2
            key3 = value3
            name = A.two
            shortname = two
        dict 2:    three
            _name_map_file = {'docs.mplx': 'A.three'}
            _short_name_map_file = {'docs.mplx': 'A.three'}
            dep = ['A.one', 'A.two']
            key1 = value1
            key2 = value2
            key3 = value3
            name = A.three
            shortname = three
        dict 3:    B.one
            _name_map_file = {'docs.mplx': 'B.one'}
            _short_name_map_file = {'docs.mplx': 'B.one'}
            dep = []
            key1 = Hello World
            key2 = some_prefix_value2
            key3 = value3
            name = B.one
            shortname = B.one
        dict 4:    B.three
            _name_map_file = {'docs.mplx': 'B.three'}
            _short_name_map_file = {'docs.mplx': 'B.three'}
            dep = ['B.one', 'B.two']
            key1 = value1
            key2 = value2
            key3 = value3
            name = B.three
            shortname = B.three

Exceptions::

    key1 = value1
    key2 = value2
    key3 = value3

    variants:
        - one:
            key1 = Hello World
            key2 <= some_prefix_
        - two: one
            key2 <= another_prefix_
        - three: one two

    variants:
        - @A:
            no one
        - B:
            only one,three

    three: key4 = some_value

    A:
        no two
        key5 = yet_another_value

Results in the following::

    Dictionaries generated:
        dict 1:    three
            _name_map_file = {'docs.mplx': 'A.three'}
            _short_name_map_file = {'docs.mplx': 'A.three'}
            dep = ['A.one', 'A.two']
            key1 = value1
            key2 = value2
            key3 = value3
            key4 = some_value
            key5 = yet_another_value
            name = A.three
            shortname = three
        dict 2:    B.one
            _name_map_file = {'docs.mplx': 'B.one'}
            _short_name_map_file = {'docs.mplx': 'B.one'}
            dep = []
            key1 = Hello World
            key2 = some_prefix_value2
            key3 = value3
            name = B.one
            shortname = B.one
        dict 3:    B.three
            _name_map_file = {'docs.mplx': 'B.three'}
            _short_name_map_file = {'docs.mplx': 'B.three'}
            dep = ['B.one', 'B.two']
            key1 = value1
            key2 = value2
            key3 = value3
            key4 = some_value
            name = B.three
            shortname = B.three

Wrap Up
=======

The multiplex config provides you with a way to specify parameters for your tests,
and also to specify complex test matrices in a concise way. You don't need to use
multiplex files as long as you are mindful to provide sensible defaults for any
params in your tests.
