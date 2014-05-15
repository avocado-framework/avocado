.. _multiplex_configuration:

=======================
Multiplex Configuration
=======================

Multiplex Configuration is a specialized way of providing lists
of key/value pairs within combination's of various categories,
that will be passed to avocado test as parameters in a dictionary
called ``params``. The format simplifies and condenses complex
multidimensional arrays of test parameters into a flat list. The
combinatorial result can be filtered and adjusted prior to testing,
with filters, dependencies, and key/value substitutions.

The parser relies on indentation, and is very sensitive to misplacement
of tab and space characters. It's highly recommended to edit/view
Multiplex Configuration files in an editor capable of collapsing tab
characters into four space characters. Improper attention to column
spacing can drastically affect output.

.. _keys_and_values:

Keys and values
===============

Keys and values are the most basic useful facility provided by the
format. A statement in the form ``<key> = <value>`` sets ``<key>`` to
``<value>``. Values are strings, terminated by a linefeed, with
surrounding quotes completely optional (but honored). A reference of
descriptions for most keys is included in section Configuration Parameter
Reference.

The key will become part of all lower-level (i.e. further indented) variant
stanzas (see section variants_). However, key precedence is evaluated in
top-down or ``last defined`` order. In other words, the last parsed key has
precedence over earlier definitions.

.. _variants:

Variants
========

A ``variants`` stanza is opened by a ``variants:`` statement. The contents
of the stanza must be indented further left than the ``variants:``
statement. Each variant stanza or block defines a single dimension of
the output array. When a Multiplex Configuration file contains
two variants stanzas, the output will be all possible combination's of
both variant contents. Variants may be nested within other variants,
effectively nesting arbitrarily complex arrays within the cells of
outside arrays.  For example::

    variants:
        - one:
            key1 = Hello
        - two:
            key2 = World
        - three:
    variants:
        - four:
            key3 = foo
        - five:
            key3 = bar
        - six:
            key1 = foo
            key2 = bar

While combining, the parser forms names for each outcome based on
prepending each variant onto a list. In other words, the first variant
name parsed will appear as the left most name component. These names can
become quite long, and since they contain keys to distinguishing between
results, a 'short-name' key is also used.

Avocado comes equipped with a plugin to parse multiplex files. The appropriate
subcommand is::

    avocado multiplex /path/to/multiplex.mplx [-c]

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

Variant shortnames represent the ``<TESTNAME>`` value used when results are
recorded (see section Job Names and Tags). For convenience
variants whose name begins with a ``@`` do not prepend their name to
``shortname``, only 'name'. This allows creating ``shortcuts`` for
specifying multiple sets or changes to key/value pairs without changing
the results directory name. For example, this is often convenient for
providing a collection of related pre-configured tests based on a
combination of others.

.. _filters:

Filters
=======

Filter statements allow modifying the resultant set of keys based on the
name of the variant set (see section variants_). Filters can be used in 3 ways:
Limiting the set to include only combination names matching a pattern.
Limiting the set to exclude all combination names not matching a
pattern. Modifying the set or contents of key/value pairs within a
matching combination name.

Names are matched by pairing a variant name component with the
character(s) ``,`` meaning ``OR``, ``..`` meaning ``AND``, and ``.`` meaning
``IMMEDIATELY-FOLLOWED-BY``. When used alone, they permit modifying the list
of key/values previously defined. For example:

::

    Linux..OpenSuse:
    initrd = initrd

Modifies all variants containing ``Linux`` followed anywhere thereafter
with ``OpenSuse``, such that the ``initrd`` key is created or overwritten
with the value ``initrd``.

When a filter is preceded by the keyword ``only`` or ``no``, it limits the
selection of variant combination's This is used where a particular set
of one or more variant combination's should be considered selectively or
exclusively. When given an extremely large matrix of variants, the
``only`` keyword is convenient to limit the result set to only those
matching the filter. Whereas the ``no`` keyword could be used to remove
particular conflicting key/value sets under other variant combination
names. For example:

::

    only Linux..Fedora..64

Would reduce an arbitrarily large matrix to only those variants whose
names contain Linux, Fedora, and 64 in them.

However, note that any of these filters may be used within named
variants as well. In this application, they are only evaluated when that
variant name is selected for inclusion (implicitly or explicitly) by a
higher-order. For example:

::

    variants:
        - one:
            key1 = Hello
    variants:
        - two:
            key2 = Complicated
        - three: one two
            key3 = World
    variants:
        - default:
            only three
            key2 =

    only default

Results in the following outcome (using -c):

::

    Dictionaries generated:
        dict 1:    default.three.one
            _name_map_file = {'docs.mplx': 'default.three.one'}
            _short_name_map_file = {'docs.mplx': 'default.three.one'}
            dep = ['default.one', 'default.two']
            key1 = Hello
            key2 =
            key3 = World
            name = default.three.one
            shortname = default.three.one

.. _value_substitutions:

Value Substitutions
===================

Value substitution allows for selectively overriding precedence and
defining part or all of a future key's value. Using a previously defined
key, it's value may be substituted in or as a another key's value. The
syntax is exactly the same as in the bash shell, where as a key's value
is substituted in wherever that key's name appears following a ``$``
character. When nesting a key within other non-key-name text, the name
should also be surrounded by ``{``, and ``}`` characters.

Replacement is context-sensitive, thereby if a key is redefined within
the same, or, higher-order block, that value will be used for future
substitutions. If a key is referenced for substitution, but hasn``t yet
been defined, no action is taken. In other words, the $key or ${key}
string will appear literally as or within the value. Nesting of
references is not supported (i.e. key substitutions within other
substitutions.

For example, if ``one = 1``, ``two = 2``, and ``three = 3``; then,
``order = ${one}${two}${three}`` results in ``order = 123``. This is
particularly handy for rooting an arbitrary complex directory tree
within a predefined top-level directory.

An example of context-sensitivity,

::

    key1 = default value
    key2 = default value

    sub = "key1: ${key1}; key2: ${key2};"

    variants:
        - one:
            key1 = Hello
            sub = "key1: ${key1}; key2: ${key2};"
        - two: one
            key2 = World
            sub = "key1: ${key1}; key2: ${key2};"
        - three: one two
            sub = "key1: ${key1}; key2: ${key2};"

Results in the following (using -c)

::

    Dictionaries generated:
        dict 1:    one
            _name_map_file = {'docs.mplx': 'one'}
            _short_name_map_file = {'docs.mplx': 'one'}
            dep = []
            key1 = Hello
            key2 = default value
            name = one
            shortname = one
            sub = key1: Hello; key2: default value;
        dict 2:    two
            _name_map_file = {'docs.mplx': 'two'}
            _short_name_map_file = {'docs.mplx': 'two'}
            dep = ['one']
            key1 = default value
            key2 = World
            name = two
            shortname = two
            sub = key1: default value; key2: World;
        dict 3:    three
            _name_map_file = {'docs.mplx': 'three'}
            _short_name_map_file = {'docs.mplx': 'three'}
            dep = ['one', 'two']
            key1 = default value
            key2 = default value
            name = three
            shortname = three
            sub = key1: default value; key2: default value;

With Keys, Values, Variants, Filters and Value Substitutions, we have most of what you
actually need to construct most multiplex files. The format also has some extra features,
that you can find in :doc:`MultiplexConfigAdvanced` should you need them.
