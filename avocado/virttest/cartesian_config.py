#!/usr/bin/python

"""
Cartesian configuration format file parser.

Filter syntax:

* ``,`` means ``OR``
* ``..`` means ``AND``
* ``.`` means ``IMMEDIATELY-FOLLOWED-BY``
* ``(xx=yy)`` where ``xx=VARIANT_NAME`` and ``yy=VARIANT_VALUE``

Example:

::

     qcow2..(guest_os=Fedora).14, RHEL.6..raw..boot, smp2..qcow2..migrate..ide

means match all dicts whose names have:

::

    (qcow2 AND ((guest_os=Fedora) IMMEDIATELY-FOLLOWED-BY 14)) OR
    ((RHEL IMMEDIATELY-FOLLOWED-BY 6) AND raw AND boot) OR
    (smp2 AND qcow2 AND migrate AND ide)

Note:

* ``qcow2..Fedora.14`` is equivalent to ``Fedora.14..qcow2``.
* ``qcow2..Fedora.14`` is not equivalent to ``qcow2..14.Fedora``.
* ``ide, scsi`` is equivalent to ``scsi, ide``.

Filters can be used in 3 ways:

::

    only <filter>
    no <filter>
    <filter>:

The last one starts a conditional block.

Formal definition: Regexp come from `python <http://docs.python.org/2/library/re.html>`__.
They're not deterministic, but more readable for people. Spaces between
terminals and nonterminals are only for better reading of definitions.

The base of the definitions come verbatim as follows:


::

    E = {\\n, #, :, "-", =, +=, <=, ?=, ?+=, ?<=, !, < , del, @, variants, include, only, no, name, value}

    N = {S, DEL, FILTER, FILTER_NAME, FILTER_GROUP, PN_FILTER_GROUP, STAT, VARIANT, VAR-TYPE, VAR-NAME, VAR-NAME-F, VAR, COMMENT, TEXT, DEPS, DEPS-NAME-F, META-DATA, IDENTIFIER}``


    I = I^n | n in N              // indentation from start of line
                                  // where n is indentation length.
    I = I^n+x | n,x in N          // indentation with shift

    start symbol = S
    end symbol = eps

    S -> I^0+x STATV | eps

    I^n    STATV
    I^n    STATV

    I^n STATV -> I^n STATV \\n I^n STATV | I^n STAT | I^n variants VARIANT
    I^n STAT -> I^n STAT \\n I^n STAT | I^n COMMENT | I^n include INC
    I^n STAT -> I^n del DEL | I^n FILTER

    DEL -> name \\n

    I^n STAT -> I^n name = VALUE | I^n name += VALUE | I^n name <= VALUE
    I^n STAT -> I^n name ?= VALUE | I^n name ?+= VALUE | I^n name ?<= VALUE

    VALUE -> TEXT \\n | 'TEXT' \\n | "TEXT" \\n

    COMMENT_BLOCK -> #TEXT | //TEXT
    COMMENT ->  COMMENT_BLOCK\\n
    COMMENT ->  COMMENT_BLOCK\\n

    TEXT = [^\\n] TEXT            //python format regexp

    I^n    variants VAR #comments:             add possibility for comment
    I^n+x       VAR-NAME: DEPS
    I^n+x+x2        STATV
    I^n         VAR-NAME:

    IDENTIFIER -> [A-Za-z0-9][A-Za-z0-9_-]*

    VARIANT -> VAR COMMENT_BLOCK\\n I^n+x VAR-NAME
    VAR -> VAR-TYPE: | VAR-TYPE META-DATA: | :         // Named | unnamed variant

    VAR-TYPE -> IDENTIFIER

    variants _name_ [xxx] [zzz=yyy] [uuu]:

    META-DATA -> [IDENTIFIER] | [IDENTIFIER=TEXT] | META-DATA META-DATA

    I^n VAR-NAME -> I^n VAR-NAME \\n I^n VAR-NAME | I^n VAR-NAME-N \\n I^n+x STATV
    VAR-NAME-N -> - @VAR-NAME-F: DEPS | - VAR-NAME-F: DEPS
    VAR-NAME-F -> [a-zA-Z0-9\\._-]+                  // Python regexp

    DEPS -> DEPS-NAME-F | DEPS-NAME-F,DEPS
    DEPS-NAME-F -> [a-zA-Z0-9\\._- ]+                // Python regexp

    INC -> name \\n


    FILTER_GROUP: STAT
        STAT

    I^n STAT -> I^n PN_FILTER_GROUP | I^n ! PN_FILTER_GROUP

    PN_FILTER_GROUP -> FILTER_GROUP: \\n I^n+x STAT
    PN_FILTER_GROUP -> FILTER_GROUP: STAT \\n I^n+x STAT

    only FILTER_GROUP
    no FILTER_GROUP

    FILTER -> only FILTER_GROUP \\n | no FILTER_GROUP \\n

    FILTER_GROUP -> FILTER_NAME
    FILTER_GROUP -> FILTER_GROUP..FILTER_GROUP
    FILTER_GROUP -> FILTER_GROUP,FILTER_GROUP

    FILTER_NAME -> FILTER_NAME.FILTER_NAME
    FILTER_NAME -> VAR-NAME-F | (VAR-NAME-F=VAR-NAME-F)

:copyright: Red Hat 2008-2013
"""

import os
import collections
import optparse
import logging
import re
import string
import sys

_reserved_keys = set(("name", "shortname", "dep"))

num_failed_cases = 5


class ParserError(Exception):

    def __init__(self, msg, line=None, filename=None, linenum=None):
        Exception.__init__(self)
        self.msg = msg
        self.line = line
        self.filename = filename
        self.linenum = linenum

    def __str__(self):
        if self.line:
            return "%s: %r (%s:%s)" % (self.msg, self.line,
                                       self.filename, self.linenum)
        else:
            return "%s (%s:%s)" % (self.msg, self.filename, self.linenum)


class LexerError(ParserError):
    pass


class MissingIncludeError(Exception):

    def __init__(self, line, filename, linenum):
        Exception.__init__(self)
        self.line = line
        self.filename = filename
        self.linenum = linenum

    def __str__(self):
        return ("%r (%s:%s): file does not exist or it's not a regular "
                "file" % (self.line, self.filename, self.linenum))


if sys.version_info[0] == 2 and sys.version_info[1] < 6:
    def enum(iterator, start_pos=0):
        for i in iterator:
            yield start_pos, i
            start_pos += 1
else:
    enum = enumerate


def _match_adjacent(block, ctx, ctx_set):
    """
    It try to match as many blocks as possible from context.

    :return: Count of matched blocks.
    """
    if block[0] not in ctx_set:
        return 0
    if len(block) == 1:
        return 1                          # First match and length is 1.
    if block[1] not in ctx_set:
        return int(ctx[-1] == block[0])   # Check match with last from ctx.
    k = 0
    i = ctx.index(block[0])
    while i < len(ctx):                   # Try to  match all of blocks.
        if k > 0 and ctx[i] != block[k]:  # Block not match
            i -= k - 1
            k = 0                         # Start from first block in next ctx.
        if ctx[i] == block[k]:
            k += 1
            if k >= len(block):           # match all of blocks
                break
            if block[k] not in ctx_set:   # block in not in whole ctx.
                break
        i += 1
    return k


def _might_match_adjacent(block, ctx, ctx_set, descendant_labels):
    matched = _match_adjacent(block, ctx, ctx_set)
    for elem in block[matched:]:        # Try to find rest of blocks in subtree
        if elem not in descendant_labels:
            # print "Can't match %s, ctx %s" % (block, ctx)
            return False
    return True


# Filter must inherit from object (otherwise type() won't work)
class Filter(object):
    __slots__ = ["filter"]

    def __init__(self, lfilter):
        self.filter = lfilter
        # print self.filter

    def match(self, ctx, ctx_set):
        for word in self.filter:  # Go through ,
            for block in word:    # Go through ..
                if _match_adjacent(block, ctx, ctx_set) != len(block):
                    break
            else:
                # print "Filter pass: %s ctx: %s" % (self.filter, ctx)
                return True       # All match
        return False

    def might_match(self, ctx, ctx_set, descendant_labels):
        # There is some posibility to match in children blocks.
        for word in self.filter:
            for block in word:
                if not _might_match_adjacent(block, ctx, ctx_set,
                                             descendant_labels):
                    break
            else:
                return True
        # print "Filter not pass: %s ctx: %s" % (self.filter, ctx)
        return False


class NoOnlyFilter(Filter):
    __slots__ = ("line")

    def __init__(self, lfilter, line):
        super(NoOnlyFilter, self).__init__(lfilter)
        self.line = line

    def __eq__(self, o):
        if isinstance(o, self.__class__):
            if self.filter == o.filter:
                return True

        return False


class OnlyFilter(NoOnlyFilter):
    # pylint: disable=W0613

    def is_irrelevant(self, ctx, ctx_set, descendant_labels):
        # Matched in this tree.
        return self.match(ctx, ctx_set)

    def requires_action(self, ctx, ctx_set, descendant_labels):
        # Impossible to match in this tree.
        return not self.might_match(ctx, ctx_set, descendant_labels)

    def might_pass(self, failed_ctx, failed_ctx_set, ctx, ctx_set,
                   descendant_labels):
        for word in self.filter:
            for block in word:
                if (_match_adjacent(block, ctx, ctx_set) >
                        _match_adjacent(block, failed_ctx, failed_ctx_set)):
                    return self.might_match(ctx, ctx_set, descendant_labels)
        return False

    def __str__(self):
        return "Only %s" % (self.filter)

    def __repr__(self):
        return "Only %s" % (self.filter)


class NoFilter(NoOnlyFilter):

    def is_irrelevant(self, ctx, ctx_set, descendant_labels):
        return not self.might_match(ctx, ctx_set, descendant_labels)

    # pylint: disable=W0613
    def requires_action(self, ctx, ctx_set, descendant_labels):
        return self.match(ctx, ctx_set)

    # pylint: disable=W0613
    def might_pass(self, failed_ctx, failed_ctx_set, ctx, ctx_set,
                   descendant_labels):
        for word in self.filter:
            for block in word:
                if (_match_adjacent(block, ctx, ctx_set) <
                        _match_adjacent(block, failed_ctx, failed_ctx_set)):
                    return not self.match(ctx, ctx_set)
        return False

    def __str__(self):
        return "No %s" % (self.filter)

    def __repr__(self):
        return "No %s" % (self.filter)


class BlockFilter(object):
    __slots__ = ["blocked"]

    def __init__(self, blocked):
        self.blocked = blocked

    def apply_to_dict(self, d):
        pass


class Condition(NoFilter):
    __slots__ = ["content"]

    # pylint: disable=W0231
    def __init__(self, lfilter, line):
        super(Condition, self).__init__(lfilter, line)
        self.content = []

    def __str__(self):
        return "Condition %s:%s" % (self.filter, self.content)

    def __repr__(self):
        return "Condition %s:%s" % (self.filter, self.content)


class NegativeCondition(OnlyFilter):
    __slots__ = ["content"]

    # pylint: disable=W0231
    def __init__(self, lfilter, line):
        super(NegativeCondition, self).__init__(lfilter, line)
        self.content = []

    def __str__(self):
        return "NotCond %s:%s" % (self.filter, self.content)

    def __repr__(self):
        return "NotCond %s:%s" % (self.filter, self.content)


class StrReader(object):

    """
    Preprocess an input string for easy reading.
    """

    def __init__(self, s):
        """
        Initialize the reader.

        :param s: The string to parse.
        """
        self.filename = "<string>"
        self._lines = []
        self._line_index = 0
        self._stored_line = None
        for linenum, line in enumerate(s.splitlines()):
            line = line.rstrip().expandtabs()
            stripped_line = line.lstrip()
            indent = len(line) - len(stripped_line)
            if (not stripped_line
                or stripped_line.startswith("#")
                    or stripped_line.startswith("//")):
                continue
            self._lines.append((stripped_line, indent, linenum + 1))

    def get_next_line(self, prev_indent):
        """
        Get the next line in the current block.

        :param prev_indent: The indentation level of the previous block.
        :return: (line, indent, linenum), where indent is the line's
            indentation level.  If no line is available, (None, -1, -1) is
            returned.
        """
        if self._stored_line:
            ret = self._stored_line
            self._stored_line = None
            return ret
        if self._line_index >= len(self._lines):
            return None, -1, -1
        line, indent, linenum = self._lines[self._line_index]
        if indent <= prev_indent:
            return None, indent, linenum
        self._line_index += 1
        return line, indent, linenum

    def set_next_line(self, line, indent, linenum):
        """
        Make the next call to get_next_line() return the given line instead of
        the real next line.
        """
        line = line.strip()
        if line:
            self._stored_line = line, indent, linenum


class FileReader(StrReader):

    """
    Preprocess an input file for easy reading.
    """

    def __init__(self, filename):
        """
        Initialize the reader.

        :parse filename: The name of the input file.
        """
        StrReader.__init__(self, open(filename).read())
        self.filename = filename


class Label(object):
    __slots__ = ["name", "var_name", "long_name", "hash_val", "hash_var"]

    def __init__(self, name, next_name=None):
        if next_name is None:
            self.name = name
            self.var_name = None
        else:
            self.name = next_name
            self.var_name = name

        if self.var_name is None:
            self.long_name = "%s" % (self.name)
        else:
            self.long_name = "(%s=%s)" % (self.var_name, self.name)

        self.hash_val = self.hash_name()
        self.hash_var = None
        if self.var_name:
            self.hash_var = self.hash_variant()

    def __str__(self):
        return self.long_name

    def __repr__(self):
        return self.long_name

    def __eq__(self, o):
        """
        The comparison is asymmetric due to optimization.
        """
        if o.var_name:
            if self.long_name == o.long_name:
                return True
        else:
            if self.name == o.name:
                return True
        return False

    def __ne__(self, o):
        """
        The comparison is asymmetric due to optimization.
        """
        if o.var_name:
            if self.long_name != o.long_name:
                return True
        else:
            if self.name != o.name:
                return True
        return False

    def __hash__(self):
        return self.hash_val

    def hash_name(self):
        return sum([i + 1 * ord(x) for i, x in enumerate(self.name)])

    def hash_variant(self):
        return sum([i + 1 * ord(x) for i, x in enumerate(str(self))])


class Node(object):
    __slots__ = ["var_name", "name", "filename", "dep", "content", "children",
                 "labels", "append_to_shortname", "failed_cases", "default",
                 "q_dict"]

    def __init__(self):
        self.var_name = []
        self.name = []
        self.filename = ""
        self.dep = []
        self.content = []
        self.children = []
        self.labels = set()
        self.append_to_shortname = False
        self.failed_cases = collections.deque()
        self.default = False

    def dump(self, indent, recurse=False):
        print("%s%s" % (" " * indent, self.name))
        print("%s%s" % (" " * indent, self.var_name))
        print("%s%s" % (" " * indent, self))
        print("%s%s" % (" " * indent, self.content))
        print("%s%s" % (" " * indent, self.failed_cases))
        if recurse:
            for child in self.children:
                child.dump(indent + 3, recurse)


match_subtitute = re.compile("\$\{(.+?)\}")


def _subtitution(value, d):
    """
    Only optimization string Template subtitute is quite expensive operation.

    :param value: String where could be $string for subtitution.
    :param d: Dictionary from which should be value subtituted to value.

    :return: Substituted string
    """
    if "$" in value:
        start = 0
        st = ""
        try:
            match = match_subtitute.search(value, start)
            while match:
                val = eval(match.group(1), None, d)
                st += value[start:match.start()] + str(val)
                start = match.end()
                match = match_subtitute.search(value, start)
        except:
            pass
        st += value[start:len(value)]
        return st
    else:
        return value


class Token(object):
    __slots__ = []
    identifier = ""

    def __str__(self):
        return self.identifier

    def __repr__(self):
        return "'%s'" % self.identifier

    def __ne__(self, o):
        """
        The comparison is asymmetric due to optimization.
        """
        if o.identifier != self.identifier:
            return True
        return False


class LIndent(Token):
    __slots__ = ["length"]
    identifier = "indent"

    def __init__(self, length):
        self.length = length

    def __str__(self):
        return "%s %s" % (self.identifier, self.length)

    def __repr__(self):
        return "%s %s" % (self.identifier, self.length)


class LEndL(Token):
    __slots__ = []
    identifier = "endl"


class LEndBlock(LIndent):
    __slots__ = []
    pass


class LIdentifier(str):
    __slots__ = []
    identifier = "Identifier re([A-Za-z0-9][A-Za-z0-9_-]*)"

    def __str__(self):
        return super(LIdentifier, self).__str__()

    def __repr__(self):
        return "'%s'" % self

    def checkChar(self, chars):
        for t in self:
            if not (t in chars):
                raise ParserError("Wrong char %s in %s" % (t, self))
        return self

    def checkAlpha(self):
        """
        Check if string contain only chars
        """
        if not self.isalpha():
            raise ParserError("Some of chars is not alpha in %s" % (self))
        return self

    def checkNumbers(self):
        """
        Check if string contain only chars
        """
        if not self.isdigit():
            raise ParserError("Some of chars is not digit in %s" % (self))
        return self

    def checkCharAlpha(self, chars):
        """
        Check if string contain only chars
        """
        for t in self:
            if not (t in chars or t.isalpha()):
                raise ParserError("Char %s is not alpha or one of special"
                                  "chars [%s] in %s" % (t, chars, self))
        return self

    def checkCharAlphaNum(self, chars):
        """
        Check if string contain only chars
        """
        for t in self:
            if not (t in chars or t.isalnum()):
                raise ParserError("Char %s is not alphanum or one of special"
                                  "chars [%s] in %s" % (t, chars, self))
        return self

    def checkCharNumeric(self, chars):
        """
        Check if string contain only chars
        """
        for t in self:
            if not (t in chars or t.isdigit()):
                raise ParserError("Char %s is not digit or one of special"
                                  "chars [%s] in %s" % (t, chars, self))
        return self


class LWhite(LIdentifier):
    __slots__ = []
    identifier = "WhiteSpace re(\\s)"


class LString(LIdentifier):
    __slots__ = []
    identifier = "String re(.+)"


class LColon(Token):
    __slots__ = []
    identifier = ":"


class LVariants(Token):
    __slots__ = []
    identifier = "variants"


class LDot(Token):
    __slots__ = []
    identifier = "."


class LVariant(Token):
    __slots__ = []
    identifier = "-"


class LDefault(Token):
    __slots__ = []
    identifier = "@"


class LOnly(Token):
    __slots__ = []
    identifier = "only"


class LNo(Token):
    __slots__ = []
    identifier = "no"


class LCond(Token):
    __slots__ = []
    identifier = ""


class LNotCond(Token):
    __slots__ = []
    identifier = "!"


class LOr(Token):
    __slots__ = []
    identifier = ","


class LAnd(Token):
    __slots__ = []
    identifier = ".."


class LCoc(Token):
    __slots__ = []
    identifier = "."


class LComa(Token):
    __slots__ = []
    identifier = ","


class LLBracket(Token):
    __slots__ = []
    identifier = "["


class LRBracket(Token):
    __slots__ = []
    identifier = "]"


class LLRBracket(Token):
    __slots__ = []
    identifier = "("


class LRRBracket(Token):
    __slots__ = []
    identifier = ")"


class LRegExpStart(Token):
    __slots__ = []
    identifier = "${"


class LRegExpStop(Token):
    __slots__ = []
    identifier = "}"


class LInclude(Token):
    __slots__ = []
    identifier = "include"


class LOperators(Token):
    __slots__ = ["name", "value"]
    identifier = ""
    function = None

    def set_operands(self, name, value):
        # pylint: disable=W0201
        self.name = str(name)
        # pylint: disable=W0201
        self.value = str(value)
        return self


class LSet(LOperators):
    __slots__ = []
    identifier = "="

    def apply_to_dict(self, d):
        """
        :param d: Dictionary for apply value
        """
        if self.name not in _reserved_keys:
            d[self.name] = _subtitution(self.value, d)


class LAppend(LOperators):
    __slots__ = []
    identifier = "+="

    def apply_to_dict(self, d):
        if self.name not in _reserved_keys:
            d[self.name] = d.get(self.name, "") + _subtitution(self.value, d)


class LPrepend(LOperators):
    __slots__ = []
    identifier = "<="

    def apply_to_dict(self, d):
        if self.name not in _reserved_keys:
            d[self.name] = _subtitution(self.value, d) + d.get(self.name, "")


class LRegExpSet(LOperators):
    __slots__ = []
    identifier = "?="

    def apply_to_dict(self, d):
        exp = re.compile("%s$" % self.name)
        value = _subtitution(self.value, d)
        for key in d:
            if key not in _reserved_keys and exp.match(key):
                d[key] = value


class LRegExpAppend(LOperators):
    __slots__ = []
    identifier = "?+="

    def apply_to_dict(self, d):
        exp = re.compile("%s$" % self.name)
        value = _subtitution(self.value, d)
        for key in d:
            if key not in _reserved_keys and exp.match(key):
                d[key] += value


class LRegExpPrepend(LOperators):
    __slots__ = []
    identifier = "?<="

    def apply_to_dict(self, d):
        exp = re.compile("%s$" % self.name)
        value = _subtitution(self.value, d)
        for key in d:
            if key not in _reserved_keys and exp.match(key):
                d[key] = value + d[key]


class LDel(LOperators):
    __slots__ = []
    identifier = "del"

    def apply_to_dict(self, d):
        exp = re.compile("%s$" % self.name)
        keys_to_del = collections.deque()
        for key in d:
            if key not in _reserved_keys and exp.match(key):
                keys_to_del.append(key)
        for key in keys_to_del:
            del d[key]


class LApplyPreDict(LOperators):
    __slots__ = []
    identifier = "apply_pre_dict"

    def set_operands(self, name, value):
        # pylint: disable=W0201
        self.name = name
        # pylint: disable=W0201
        self.value = value
        return self

    def apply_to_dict(self, d):
        d.update(self.value)

    def __str__(self):
        return "Apply_pre_dict: %s" % self.value

    def __repr__(self):
        return "Apply_pre_dict: %s" % self.value


class LUpdateFileMap(LOperators):
    __slots__ = ["shortname", "dest"]
    identifier = "update_file_map"

    def set_operands(self, filename, name, dest="_name_map_file"):
        # pylint: disable=W0201
        self.name = name
        # pylint: disable=W0201
        if filename == "<string>":
            self.shortname = filename
        else:
            self.shortname = os.path.basename(filename)

        self.dest = dest
        return self

    def apply_to_dict(self, d):
        dest = self.dest
        if dest not in d:
            d[dest] = {}

        if self.shortname in d[dest]:
            old_name = d[dest][self.shortname]
            d[dest][self.shortname] = "%s.%s" % (self.name, old_name)
        else:
            d[dest][self.shortname] = self.name


spec_iden = "_-"
spec_oper = "+<?"


tokens_map = {"-": LVariant,
              ".": LDot,
              ":": LColon,
              "@": LDefault,
              ",": LComa,
              "[": LLBracket,
              "]": LRBracket,
              "(": LLRBracket,
              ")": LRRBracket,
              "!": LNotCond}


tokens_oper = {"": LSet,
               "+": LAppend,
               "<": LPrepend,
               "?": LRegExpSet,
               "?+": LRegExpAppend,
               "?<": LRegExpPrepend,
               }


tokens_oper_re = [r"\=", r"\+\=", r"\<\=", r"\?\=", r"\?\+\=", r"\?\<\="]


_ops_exp = re.compile(r"|".join(tokens_oper_re))


class Lexer(object):

    def __init__(self, reader):
        self.reader = reader
        self.filename = reader.filename
        self.line = None
        self.linenum = 0
        self.ignore_white = False
        self.rest_as_string = False
        self.match_func_index = 0
        self.generator = self.get_lexer()
        self.prev_indent = 0
        self.fast = False

    def set_prev_indent(self, prev_indent):
        self.prev_indent = prev_indent

    def set_fast(self):
        self.fast = True

    def set_strict(self):
        self.fast = False

    def match(self, line, pos):
        l0 = line[0]
        chars = ""
        m = None
        cind = 0
        if l0 == "v":
            if line.startswith("variants:"):
                yield LVariants()
                yield LColon()
                pos = 9
            elif line.startswith("variants "):
                yield LVariants()
                pos = 8
        elif l0 == "-":
            yield LVariant()
            pos = 1
        elif l0 == "o":
            if line.startswith("only "):
                yield LOnly()
                pos = 4
                while line[pos].isspace():
                    pos += 1
        elif l0 == "n":
            if line.startswith("no "):
                yield LNo()
                pos = 2
                while line[pos].isspace():
                    pos += 1
        elif l0 == "i":
            if line.startswith("include "):
                yield LInclude()
                pos = 7
        elif l0 == "d":
            if line.startswith("del "):
                yield LDel()
                pos = 3
                while line[pos].isspace():
                    pos += 1

        if self.fast and pos == 0:  # due to refexp
            cind = line[pos:].find(":")
            m = _ops_exp.search(line[pos:])

        oper = ""
        token = None

        if self.rest_as_string:
            self.rest_as_string = False
            yield LString(line[pos:].lstrip())
        elif self.fast and m and (cind < 0 or cind > m.end()):
            chars = ""
            yield LIdentifier(line[:m.start()].rstrip())
            yield tokens_oper[m.group()[:-1]]()
            yield LString(line[m.end():].lstrip())
        else:
            li = enum(line[pos:], pos)
            for pos, char in li:
                if char.isalnum() or char in spec_iden:    # alfanum+_-
                    chars += char
                elif char in spec_oper:     # <+?=
                    if chars:
                        yield LIdentifier(chars)
                        oper = ""
                    chars = ""
                    oper += char
                else:
                    if chars:
                        yield LIdentifier(chars)
                        chars = ""
                    if char.isspace():   # Whitespace
                        for pos, char in li:
                            if not char.isspace():
                                if not self.ignore_white:
                                    yield LWhite()
                                break
                    if char.isalnum() or char in spec_iden:
                        chars += char
                    elif char == "=":
                        if oper in tokens_oper:
                            yield tokens_oper[oper]()
                        else:
                            raise LexerError("Unexpected character %s on"
                                             " pos %s" % (char, pos),
                                             self.line, self.filename,
                                             self.linenum)
                        oper = ""
                    elif char in tokens_map:
                        token = tokens_map[char]()
                    elif char == "\"":
                        chars = ""
                        pos, char = li.next()
                        while char != "\"":
                            chars += char
                            pos, char = li.next()
                        yield LString(chars)
                    elif char == "#":
                        break
                    elif char in spec_oper:
                        oper += char
                    else:
                        raise LexerError("Unexpected character %s on"
                                         " pos %s. Special chars are allowed"
                                         " only in variable assignation"
                                         " statement" % (char, pos), line,
                                         self.filename, self.linenum)
                    if token is not None:
                        yield token
                        token = None
                    if self.rest_as_string:
                        self.rest_as_string = False
                        yield LString(line[pos + 1:].lstrip())
                        break
        if chars:
            yield LIdentifier(chars)
            chars = ""
        yield LEndL()

    def get_lexer(self):
        cr = self.reader
        indent = 0
        while True:
            (self.line, indent,
             self.linenum) = cr.get_next_line(self.prev_indent)

            if not self.line:
                yield LEndBlock(indent)
                continue

            yield LIndent(indent)
            for token in self.match(self.line, 0):
                yield token

    def get_until_gen(self, end_tokens=None):
        if end_tokens is None:
            end_tokens = [LEndL]
        token = self.generator.next()
        while type(token) not in end_tokens:
            yield token
            token = self.generator.next()
        yield token

    def get_until(self, end_tokens=None):
        if end_tokens is None:
            end_tokens = [LEndL]
        return [x for x in self.get_until_gen(end_tokens)]

    def flush_until(self, end_tokens=None):
        if end_tokens is None:
            end_tokens = [LEndL]
        for _ in self.get_until_gen(end_tokens):
            pass

    def get_until_check(self, lType, end_tokens=None):
        """
        Read tokens from iterator until get end_tokens or type of token not
        match ltype

        :param lType: List of allowed tokens
        :param end_tokens: List of tokens for end reading
        :return: List of readed tokens.
        """
        if end_tokens is None:
            end_tokens = [LEndL]
        tokens = []
        lType = lType + end_tokens
        for token in self.get_until_gen(end_tokens):
            if type(token) in lType:
                tokens.append(token)
            else:
                raise ParserError("Expected %s got %s" % (lType, type(token)),
                                  self.line, self.filename, self.linenum)
        return tokens

    def get_until_no_white(self, end_tokens=None):
        """
        Read tokens from iterator until get one of end_tokens and strip LWhite

        :param end_tokens:  List of tokens for end reading
        :return: List of readed tokens.
        """
        if end_tokens is None:
            end_tokens = [LEndL]
        return [x for x in self.get_until_gen(end_tokens) if type(x) != LWhite]

    def rest_line_gen(self):
        token = self.generator.next()
        while type(token) != LEndL:
            yield token
            token = self.generator.next()

    def rest_line(self):
        return [x for x in self.rest_line_gen()]

    def rest_line_no_white(self):
        return [x for x in self.rest_line_gen() if type(x) != LWhite]

    def rest_line_as_LString(self):
        self.rest_as_string = True
        lstr = self.generator.next()
        self.generator.next()
        return lstr

    def get_next_check(self, lType):
        token = self.generator.next()
        if type(token) in lType:
            return type(token), token
        else:
            raise ParserError("Expected %s got ['%s']=[%s]" %
                              ([x.identifier for x in lType],
                               token.identifier, token),
                              self.line, self.filename, self.linenum)

    def get_next_check_nw(self, lType):
        token = self.generator.next()
        while type(token) == LWhite:
            token = self.generator.next()
        if type(token) in lType:
            return type(token), token
        else:
            raise ParserError("Expected %s got ['%s']" %
                              ([x.identifier for x in lType],
                               token.identifier),
                              self.line, self.filename, self.linenum)

    def check_token(self, token, lType):
        if type(token) in lType:
            return type(token), token
        else:
            raise ParserError("Expected %s got ['%s']" %
                              ([x.identifier for x in lType],
                               token.identifier),
                              self.line, self.filename, self.linenum)


def next_nw(gener):
    token = gener.next()
    while type(token) == LWhite:
        token = gener.next()
    return token


def cmd_tokens(tokens1, tokens2):
    for x, y in zip(tokens1, tokens2):
        if x != y:
            return False
    else:
        return True


def apply_predict(lexer, node, pre_dict):
    predict = LApplyPreDict().set_operands(None, pre_dict)
    node.content += [(lexer.filename, lexer.linenum, predict)]
    return {}


def parse_filter(lexer, tokens):
    """
    :return: Parsed filter
    """
    or_filters = []
    tokens = iter(tokens + [LEndL()])
    typet, token = lexer.check_token(tokens.next(), [LIdentifier, LLRBracket,
                                                     LEndL, LWhite])
    and_filter = []
    con_filter = []
    dots = 1
    while typet not in [LEndL]:
        if typet in [LIdentifier, LLRBracket]:        # join    identifier
            if typet == LLRBracket:    # (xxx=ttt)
                _, ident = lexer.check_token(next_nw(tokens),
                                             [LIdentifier])  # (iden
                typet, _ = lexer.check_token(next_nw(tokens),
                                             [LSet, LRRBracket])  # =
                if typet == LRRBracket:  # (xxx)
                    token = Label(str(ident))
                elif typet == LSet:    # (xxx = yyyy)
                    _, value = lexer.check_token(next_nw(tokens),
                                                 [LIdentifier, LString])
                    lexer.check_token(next_nw(tokens), [LRRBracket])
                    token = Label(str(ident), str(value))
            else:
                token = Label(token)
            if dots == 1:
                con_filter.append(token)
            elif dots == 2:
                and_filter.append(con_filter)
                con_filter = [token]
            elif dots == 0 or dots > 2:
                raise ParserError("Syntax Error expected \".\" between"
                                  " Identifier.", lexer.line, lexer.filename,
                                  lexer.linenum)

            dots = 0
        elif typet == LDot:         # xxx.xxxx or xxx..xxxx
            dots += 1
        elif typet in [LComa, LWhite]:
            if dots > 0:
                raise ParserError("Syntax Error expected identifier between"
                                  " \".\" and \",\".", lexer.line,
                                  lexer.filename, lexer.linenum)
            if and_filter:
                if con_filter:
                    and_filter.append(con_filter)
                    con_filter = []
                or_filters.append(and_filter)
                and_filter = []
            elif con_filter:
                or_filters.append([con_filter])
                con_filter = []
            elif typet == LIdentifier:
                or_filters.append([[Label(token)]])
            else:
                raise ParserError("Syntax Error expected \",\" between"
                                  " Identifier.", lexer.line, lexer.filename,
                                  lexer.linenum)
            dots = 1
            token = tokens.next()
            while type(token) == LWhite:
                token = tokens.next()
            typet, token = lexer.check_token(token, [LIdentifier,
                                                     LComa, LDot,
                                                     LLRBracket, LEndL])
            continue
        typet, token = lexer.check_token(tokens.next(), [LIdentifier, LComa,
                                                         LDot, LLRBracket,
                                                         LEndL, LWhite])
    if and_filter:
        if con_filter:
            and_filter.append(con_filter)
            con_filter = []
        or_filters.append(and_filter)
        and_filter = []
    if con_filter:
        or_filters.append([con_filter])
        con_filter = []
    return or_filters


class Parser(object):
    # pylint: disable=W0102

    def __init__(self, filename=None, defaults=False, expand_defaults=[],
                 debug=False):
        self.node = Node()
        self.debug = debug
        self.defaults = defaults
        self.expand_defaults = [LIdentifier(x) for x in expand_defaults]

        self.filename = filename
        if self.filename:
            self.parse_file(self.filename)

        self.only_filters = []
        self.no_filters = []
        self.assignments = []

    def _debug(self, s, *args):
        if self.debug:
            logging.debug(s, *args)

    def _warn(self, s, *args):
        logging.warn(s, *args)

    def parse_file(self, filename):
        """
        Parse a file.

        :param filename: Path of the configuration file.
        """
        self.node.filename = filename
        self.node = self._parse(Lexer(FileReader(filename)), self.node)
        self.filename = filename

    def parse_string(self, s):
        """
        Parse a string.

        :param s: String to parse.
        """
        self.node.filename = StrReader("").filename
        self.node = self._parse(Lexer(StrReader(s)), self.node)

    def only_filter(self, variant):
        """
        Apply a only filter programatically and keep track of it.

        Equivalent to parse a "only variant" line.

        :param variant: String with the variant name.
        """
        string = "only %s" % variant
        self.only_filters.append(string)
        self.parse_string(string)

    def no_filter(self, variant):
        """
        Apply a only filter programatically and keep track of it.

        Equivalent to parse a "no variant" line.

        :param variant: String with the variant name.
        """
        string = "no %s" % variant
        self.only_filters.append(string)
        self.parse_string(string)

    def assign(self, key, value):
        """
        Apply a only filter programatically and keep track of it.

        Equivalent to parse a "key = value" line.

        :param variant: String with the variant name.
        """
        string = "%s = %s" % (key, value)
        self.assignments.append(string)
        self.parse_string(string)

    def _parse(self, lexer, node=None, prev_indent=-1):
        if not node:
            node = self.node
        block_allowed = [LVariants, LIdentifier, LOnly,
                         LNo, LInclude, LDel, LNotCond]

        variants_allowed = [LVariant]

        identifier_allowed = [LSet, LAppend, LPrepend,
                              LRegExpSet, LRegExpAppend,
                              LRegExpPrepend, LColon,
                              LEndL]

        varianst_allowed_in = [LLBracket, LColon, LIdentifier, LEndL]
        indent_allowed = [LIndent, LEndBlock]

        allowed = block_allowed
        var_indent = 0
        var_name = ""
        # meta contains variants meta-data
        meta = {}
        # pre_dict contains block of operation without collision with
        # others block or operation. Increase speed almost twice.
        pre_dict = {}
        lexer.set_fast()
        try:
            while True:
                lexer.set_prev_indent(prev_indent)
                typet, token = lexer.get_next_check(indent_allowed)
                if typet == LEndBlock:
                    if pre_dict:
                        # flush pre_dict to node content.
                        pre_dict = apply_predict(lexer, node, pre_dict)
                    return node

                indent = token.length
                typet, token = lexer.get_next_check(allowed)

                if typet == LIdentifier:
                    # Parse:
                    #    identifier .....
                    identifier = lexer.get_until_no_white(identifier_allowed)
                    if isinstance(identifier[-1], LOperators):  # operand = <=
                        # Parse:
                        #    identifier = xxx
                        #    identifier <= xxx
                        #    identifier ?= xxx
                        #    etc..
                        op = identifier[-1]
                        if (len(identifier) == 1):
                            identifier = token
                        else:
                            identifier = [token] + identifier[:-1]
                            identifier = "".join([str(x) for x in identifier])
                        _, value = lexer.get_next_check([LString])
                        if value and (value[0] == value[-1] == '"' or
                                      value[0] == value[-1] == "'"):
                            value = value[1:-1]

                        op.set_operands(identifier, value)
                        d_nin_val = "$" not in value
                        if type(op) == LSet and d_nin_val:  # Optimization
                            op.apply_to_dict(pre_dict)
                        else:
                            if pre_dict:
                                # flush pre_dict to node content.
                                # If block already contain xxx = yyyy
                                # then operation xxx +=, <=, .... are safe.
                                if op.name in pre_dict and d_nin_val:
                                    op.apply_to_dict(pre_dict)
                                    lexer.get_next_check([LEndL])
                                    continue
                                else:
                                    pre_dict = apply_predict(lexer, node,
                                                             pre_dict)

                            node.content += [(lexer.filename,
                                              lexer.linenum,
                                              op)]
                        lexer.get_next_check([LEndL])

                    elif type(identifier[-1]) == LColon:  # condition:
                        # Parse:
                        #    xxx.yyy.(aaa=bbb):
                        identifier = [token] + identifier[:-1]
                        cfilter = parse_filter(lexer, identifier + [LEndL()])
                        next_line = lexer.rest_line_as_LString()
                        if next_line != "":
                            lexer.reader.set_next_line(next_line, indent + 1,
                                                       lexer.linenum)
                        cond = Condition(cfilter, lexer.line)
                        self._parse(lexer, cond, prev_indent=indent)

                        pre_dict = apply_predict(lexer, node, pre_dict)
                        node.content += [(lexer.filename, lexer.linenum, cond)]
                    else:
                        raise ParserError("Syntax ERROR expected \":\" or"
                                          " operand", lexer.line,
                                          lexer.filename, lexer.linenum)

                elif typet == LVariant:
                    # Parse
                    #  - var1: depend1, depend2
                    #      block1
                    #  - var2:
                    #      block2
                    if pre_dict:
                        pre_dict = apply_predict(lexer, node, pre_dict)
                    already_default = False
                    is_default = False
                    meta_with_default = False
                    if "default" in meta:
                        meta_with_default = True
                    meta_in_expand_defautls = False
                    if var_name not in self.expand_defaults:
                        meta_in_expand_defautls = True
                    node4 = Node()
                    while True:
                        lexer.set_prev_indent(var_indent)
                        # Get token from lexer and check syntax.
                        typet, token = lexer.get_next_check_nw([LIdentifier,
                                                                LDefault,
                                                                LIndent,
                                                                LEndBlock])
                        if typet == LEndBlock:
                            break

                        if typet == LIndent:
                            lexer.get_next_check_nw([LVariant])
                            typet, token = lexer.get_next_check_nw(
                                [LIdentifier,
                                 LDefault])

                        if typet == LDefault:  # @
                            is_default = True
                            name = lexer.get_until_check([LIdentifier, LDot],
                                                         [LColon])
                        else:  # identificator
                            is_default = False
                            name = [token] + lexer.get_until_check(
                                [LIdentifier, LDot],
                                [LColon])

                        if len(name) == 2:
                            name = [name[0]]
                            raw_name = name
                        else:
                            raw_name = [x for x in name[:-1]]
                            name = [x for x in name[:-1]
                                    if type(x) == LIdentifier]

                        token = lexer.generator.next()
                        while type(token) == LWhite:
                            token = lexer.generator.next()
                        tokens = None
                        if type(token) != LEndL:
                            tokens = [token] + lexer.get_until([LEndL])
                            deps = parse_filter(lexer, tokens)
                        else:
                            deps = []

                        # Prepare data for dict generator.
                        node2 = Node()
                        node2.children = [node]
                        node2.labels = node.labels

                        if var_name:
                            op = LSet().set_operands(var_name,
                                                     ".".join([str(n) for n in name]))
                            node2.content += [(lexer.filename,
                                               lexer.linenum,
                                               op)]

                        node3 = self._parse(lexer, node2, prev_indent=indent)

                        if var_name:
                            node3.var_name = var_name
                            node3.name = [Label(var_name, str(n))
                                          for n in name]
                        else:
                            node3.name = [Label(str(n)) for n in name]

                        # Update mapping name to file

                        node3.dep = deps

                        if meta_with_default:
                            for wd in meta["default"]:
                                if cmd_tokens(wd, raw_name):
                                    is_default = True
                                    meta["default"].remove(wd)

                        if (is_default and not already_default and
                                meta_in_expand_defautls):
                            node3.default = True
                            already_default = True

                        node3.append_to_shortname = not is_default

                        op = LUpdateFileMap()
                        op.set_operands(lexer.filename,
                                        ".".join(str(x)
                                                 for x in node3.name))
                        node3.content += [(lexer.filename,
                                           lexer.linenum,
                                           op)]

                        op = LUpdateFileMap()
                        op.set_operands(lexer.filename,
                                        ".".join(str(x.name)
                                                 for x in node3.name),
                                        "_short_name_map_file")
                        node3.content += [(lexer.filename,
                                           lexer.linenum,
                                           op)]

                        if node3.default and self.defaults:
                            # Move default variant in front of rest
                            # of all variants.
                            # Speed optimization.
                            node4.children.insert(0, node3)
                        else:
                            node4.children += [node3]
                        node4.labels.update(node3.labels)
                        node4.labels.update(node3.name)

                    if "default" in meta and meta["default"]:
                        raise ParserError("Missing default variant %s" %
                                          (meta["default"]), lexer.line,
                                          lexer.filename, lexer.linenum)
                    allowed = block_allowed
                    node = node4

                elif typet == LVariants:  # _name_ [meta1=xxx] [yyy] [xxx]
                    # Parse
                    #    variants _name_ [meta1] [meta2]:
                    if type(node) in [Condition, NegativeCondition]:
                        raise ParserError("'variants' is not allowed inside a "
                                          "conditional block", lexer.line,
                                          lexer.reader.filename, lexer.linenum)

                    lexer.set_strict()
                    tokens = lexer.get_until_no_white([LLBracket, LColon,
                                                       LIdentifier, LEndL])
                    vtypet = type(tokens[-1])
                    var_name = ""
                    meta.clear()
                    # [meta1=xxx] [yyy] [xxx]
                    while vtypet not in [LColon, LEndL]:
                        if vtypet == LIdentifier:
                            if var_name != "":
                                raise ParserError("Syntax ERROR expected"
                                                  " \"[\" or \":\"",
                                                  lexer.line, lexer.filename,
                                                  lexer.linenum)
                            var_name = tokens[0]
                        elif vtypet == LLBracket:  # [
                            _, ident = lexer.get_next_check_nw([LIdentifier])
                            typet, _ = lexer.get_next_check_nw([LSet,
                                                                LRBracket])
                            if typet == LRBracket:  # [xxx]
                                if ident not in meta:
                                    meta[ident] = []
                                meta[ident].append(True)
                            elif typet == LSet:  # [xxx = yyyy]
                                tokens = lexer.get_until_no_white([LRBracket,
                                                                   LEndL])
                                if type(tokens[-1]) == LRBracket:
                                    if ident not in meta:
                                        meta[ident] = []
                                    meta[ident].append(tokens[:-1])
                                else:
                                    raise ParserError("Syntax ERROR"
                                                      " expected \"]\"",
                                                      lexer.line,
                                                      lexer.filename,
                                                      lexer.linenum)

                        tokens = lexer.get_next_check_nw(varianst_allowed_in)
                        vtypet = type(tokens[-1])

                    if "default" in meta:
                        for wd in meta["default"]:
                            if type(wd) != list:
                                raise ParserError("Syntax ERROR expected "
                                                  "[default=xxx]",
                                                  lexer.line,
                                                  lexer.filename,
                                                  lexer.linenum)

                    if vtypet == LEndL:
                        raise ParserError("Syntax ERROR expected \":\"",
                                          lexer.line, lexer.filename,
                                          lexer.linenum)
                    lexer.get_next_check_nw([LEndL])
                    allowed = variants_allowed
                    var_indent = indent

                elif typet in [LNo, LOnly]:
                    # Parse:
                    #    only/no (filter=text)..aaa.bbb, xxxx
                    lfilter = parse_filter(lexer, lexer.rest_line())

                    pre_dict = apply_predict(lexer, node, pre_dict)
                    if typet == LOnly:
                        node.content += [(lexer.filename, lexer.linenum,
                                          OnlyFilter(lfilter, lexer.line))]
                    else:  # LNo
                        node.content += [(lexer.filename, lexer.linenum,
                                          NoFilter(lfilter, lexer.line))]

                elif typet == LInclude:
                    # Parse:
                    #    include relative file patch to working directory.
                    path = lexer.rest_line_as_LString()
                    filename = os.path.expanduser(path)
                    if (isinstance(lexer.reader, FileReader) and
                            not os.path.isabs(filename)):
                        filename = os.path.join(
                            os.path.dirname(lexer.filename),
                            filename)
                    if not os.path.isfile(filename):
                        raise MissingIncludeError(lexer.line, lexer.filename,
                                                  lexer.linenum)
                    pre_dict = apply_predict(lexer, node, pre_dict)
                    lch = Lexer(FileReader(filename))
                    node = self._parse(lch, node, -1)
                    lexer.set_prev_indent(prev_indent)

                elif typet == LDel:
                    # Parse:
                    #    del operand
                    _, to_del = lexer.get_next_check_nw([LIdentifier])
                    lexer.get_next_check_nw([LEndL])
                    token.set_operands(to_del, None)

                    pre_dict = apply_predict(lexer, node, pre_dict)
                    node.content += [(lexer.filename, lexer.linenum,
                                      token)]

                elif typet == LNotCond:
                    # Parse:
                    #    !xxx.yyy.(aaa=bbb): vvv
                    lfilter = parse_filter(lexer,
                                           lexer.get_until_no_white(
                                               [LColon, LEndL])[:-1])
                    next_line = lexer.rest_line_as_LString()
                    if next_line != "":
                        lexer.reader.set_next_line(next_line, indent + 1,
                                                   lexer.linenum)
                    cond = NegativeCondition(lfilter, lexer.line)
                    self._parse(lexer, cond, prev_indent=indent)
                    lexer.set_prev_indent(prev_indent)

                    pre_dict = apply_predict(lexer, node, pre_dict)
                    node.content += [(lexer.filename, lexer.linenum, cond)]
                else:
                    raise ParserError("Syntax ERROR expected", lexer.line,
                                      lexer.filename, lexer.linenum)
        except Exception:
            self._debug("%s  %s:  %s" % (lexer.filename, lexer.linenum,
                                         lexer.line))
            raise

    def get_dicts(self, node=None, ctx=[], content=[], shortname=[], dep=[]):
        """
        Generate dictionaries from the code parsed so far.  This should
        be called after parsing something.

        :return: A dict generator.
        """
        def process_content(content, failed_filters):
            # 1. Check that the filters in content are OK with the current
            #    context (ctx).
            # 2. Move the parts of content that are still relevant into
            #    new_content and unpack conditional blocks if appropriate.
            #    For example, if an 'only' statement fully matches ctx, it
            #    becomes irrelevant and is not appended to new_content.
            #    If a conditional block fully matches, its contents are
            #    unpacked into new_content.
            # 3. Move failed filters into failed_filters, so that next time we
            #    reach this node or one of its ancestors, we'll check those
            #    filters first.
            blocked_filters = []
            for t in content:
                filename, linenum, obj = t
                if isinstance(obj, LOperators):
                    new_content.append(t)
                    continue
                # obj is an OnlyFilter/NoFilter/Condition/NegativeCondition
                if obj.requires_action(ctx, ctx_set, labels):
                    # This filter requires action now
                    if type(obj) is OnlyFilter or type(obj) is NoFilter:
                        if obj not in blocked_filters:
                            self._debug("    filter did not pass: %r (%s:%s)",
                                        obj.line, filename, linenum)
                            failed_filters.append(t)
                            return False
                        else:
                            continue
                    else:
                        self._debug("    conditional block matches:"
                                    " %r (%s:%s)", obj.line, filename, linenum)
                        # Check and unpack the content inside this Condition
                        # object (note: the failed filters should go into
                        # new_internal_filters because we don't expect them to
                        # come from outside this node, even if the Condition
                        # itself was external)
                        if not process_content(obj.content,
                                               new_internal_filters):
                            failed_filters.append(t)
                            return False
                        continue
                elif obj.is_irrelevant(ctx, ctx_set, labels):
                    # This filter is no longer relevant and can be removed
                    continue
                else:
                    # Keep the filter and check it again later
                    new_content.append(t)
            return True

        def might_pass(failed_ctx,
                       failed_ctx_set,
                       failed_external_filters,
                       failed_internal_filters):
            all_content = content + node.content
            for t in failed_external_filters + failed_internal_filters:
                if t not in all_content:
                    return True
            for t in failed_external_filters:
                _, _, external_filter = t
                if not external_filter.might_pass(failed_ctx,
                                                  failed_ctx_set,
                                                  ctx, ctx_set,
                                                  labels):
                    return False
            for t in failed_internal_filters:
                if t not in node.content:
                    return True

            for t in failed_internal_filters:
                _, _, internal_filter = t
                if not internal_filter.might_pass(failed_ctx,
                                                  failed_ctx_set,
                                                  ctx, ctx_set,
                                                  labels):
                    return False
            return True

        def add_failed_case():
            node.failed_cases.appendleft((ctx, ctx_set,
                                          new_external_filters,
                                          new_internal_filters))
            if len(node.failed_cases) > num_failed_cases:
                node.failed_cases.pop()

        node = node or self.node
        # if self.debug:    #Print dict on which is working now.
        #    node.dump(0)
        # Update dep
        for d in node.dep:
            for dd in d:
                dep = dep + [".".join([str(label) for label in ctx + dd])]
        # Update ctx
        ctx = ctx + node.name
        ctx_set = set(ctx)
        labels = node.labels
        # Get the current name
        name = ".".join([str(label) for label in ctx])

        if node.name:
            self._debug("checking out %r", name)

        # Check previously failed filters
        for i, failed_case in enumerate(node.failed_cases):
            # pylint: disable=W0142
            if not might_pass(*failed_case):
                self._debug("\n*    this subtree has failed before %s\n"
                            "         content: %s\n"
                            "         failcase:%s\n",
                            name, content + node.content, failed_case)
                del node.failed_cases[i]
                node.failed_cases.appendleft(failed_case)
                return
        # Check content and unpack it into new_content
        new_content = []
        new_external_filters = []
        new_internal_filters = []
        if (not process_content(node.content, new_internal_filters) or
                not process_content(content, new_external_filters)):
            add_failed_case()
            self._debug("Failed_cases %s", node.failed_cases)
            return

        # Update shortname
        if node.append_to_shortname:
            shortname = shortname + node.name

        # Recurse into children
        count = 0
        if self.defaults and node.var_name not in self.expand_defaults:
            for n in node.children:
                for d in self.get_dicts(n, ctx, new_content, shortname, dep):
                    count += 1
                    yield d
                if n.default and count:
                    break
        else:
            for n in node.children:
                for d in self.get_dicts(n, ctx, new_content, shortname, dep):
                    count += 1
                    yield d
        # Reached leaf?
        if not node.children:
            self._debug("    reached leaf, returning it")
            d = {"name": name, "dep": dep,
                 "shortname": ".".join([str(sn.name) for sn in shortname])}
            for _, _, op in new_content:
                op.apply_to_dict(d)
            yield d
        # If this node did not produce any dicts, remember the failed filters
        # of its descendants
        elif not count:
            new_external_filters = []
            new_internal_filters = []
            for n in node.children:
                (_, _,
                 failed_external_filters,
                 failed_internal_filters) = n.failed_cases[0]
                for obj in failed_internal_filters:
                    if obj not in new_internal_filters:
                        new_internal_filters.append(obj)
                for obj in failed_external_filters:
                    if obj in content:
                        if obj not in new_external_filters:
                            new_external_filters.append(obj)
                    else:
                        if obj not in new_internal_filters:
                            new_internal_filters.append(obj)
            add_failed_case()


def print_dicts_default(options, dicts):
    """Print dictionaries in the default mode"""
    for i, d in enumerate(dicts):
        if options.fullname:
            print "dict %4d:  %s" % (i + 1, d["name"])
        else:
            print "dict %4d:  %s" % (i + 1, d["shortname"])
        if options.contents:
            keys = d.keys()
            keys.sort()
            for key in keys:
                print "    %s = %s" % (key, d[key])


# pylint: disable=W0613
def print_dicts_repr(options, dicts):
    import pprint
    print "["
    for d in dicts:
        print "%s," % (pprint.pformat(d))
    print "]"


def print_dicts(options, dicts):
    if options.repr_mode:
        print_dicts_repr(options, dicts)
    else:
        print_dicts_default(options, dicts)


if __name__ == "__main__":
    parser = optparse.OptionParser('usage: %prog [options] filename '
                                   '[extra code] ...\n\nExample:\n\n    '
                                   '%prog tests.cfg "only my_set" "no qcow2"')
    parser.add_option("-v", "--verbose", dest="debug", action="store_true",
                      help="include debug messages in console output")
    parser.add_option("-f", "--fullname", dest="fullname", action="store_true",
                      help="show full dict names instead of short names")
    parser.add_option("-c", "--contents", dest="contents", action="store_true",
                      help="show dict contents")
    parser.add_option("-r", "--repr", dest="repr_mode", action="store_true",
                      help="output parsing results Python format")
    parser.add_option("-d", "--defaults", dest="defaults", action="store_true",
                      help="use only default variant of variants if there"
                           " is some")
    parser.add_option("-e", "--expand", dest="expand", type="string",
                      help="list of vartiant which should be expanded when"
                           " defaults is enabled.  \"name, name, name\"")

    options, args = parser.parse_args()
    if not args:
        parser.error("filename required")

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)

    expand = []
    if options.expand:
        expand = [x.strip() for x in options.expand.split(",")]
    c = Parser(args[0], defaults=options.defaults, expand_defaults=expand,
               debug=options.debug)
    for s in args[1:]:
        c.parse_string(s)

    if options.debug:
        c.node.dump(0, True)

    dicts = c.get_dicts()
    print_dicts(options, dicts)
