import unittest

from avocado.core.safeloader.docstring import (
    DOCSTRING_DIRECTIVE_RE, check_docstring_directive,
    get_docstring_directives, get_docstring_directives_requirements,
    get_docstring_directives_tags)


class DocstringDirectives(unittest.TestCase):

    VALID_DIRECTIVES = [":avocado: foo",
                        " :avocado: foo",
                        " :avocado: foo ",
                        ":avocado:\tfoo",
                        ":avocado: \tfoo",
                        ":avocado: foo:",
                        ":avocado: foo=",
                        ":avocado: foo=bar:123",
                        ":avocado: 42=life",
                        ":avocado: foo,bar,baz",
                        ":avocado: foo,bar,baz:extra",
                        ":avocado: a=,,,",
                        ":avocado: a=x:y:z,None"]

    INVALID_DIRECTIVES = [":avocado:\nfoo",
                          ":avocado: \nfoo",
                          ":avocado:foo",
                          ":avocado:_foo",
                          ":avocado: ?notsure",
                          ":avocado: ,foo,bar,baz",
                          ":avocado: foo,bar,baz!!!",
                          ":avocado: =",
                          ":avocado: ,"]

    NO_TAGS = [":AVOCADO: TAGS:FAST",
               ":AVOCADO: TAGS=FAST",
               ":avocado: mytags=fast",
               ":avocado: tags",
               ":avocado: tag",
               ":avocado: tag=",
               ":this is not avocado: tags=foo",
               ":neither is this :avocado: tags:foo",
               ":tags:foo,bar",
               "tags=foo,bar",
               ":avocado: tags=SLOW,disk, invalid",
               ":avocado: tags=SLOW,disk , invalid"]

    NO_REQS = [":AVOCADO: REQUIREMENT=['FOO':'BAR']",
               ":avocado: requirement={'foo':'bar'}",
               ":avocado: requirement={foo",
               ":avocado: requirements=",
               ":avocado: requirement="]

    def test_longline(self):
        docstring = ("This is a very long docstring in a single line. "
                     "Since we have nothing useful to put in here let's just "
                     "mention avocado: it's awesome, but that was not a "
                     "directive. a tag would be something line this: "
                     ":avocado: enable")
        self.assertIsNotNone(get_docstring_directives(docstring))

    def test_newlines(self):
        docstring = ("\n\n\nThis is a docstring with many new\n\nlines "
                     "followed by an avocado tag\n"
                     "\n\n:avocado: enable\n\n")
        self.assertIsNotNone(get_docstring_directives(docstring))

    def test_enabled(self):
        self.assertTrue(check_docstring_directive(":avocado: enable", 'enable'))
        self.assertTrue(check_docstring_directive(":avocado:\tenable", 'enable'))
        self.assertTrue(check_docstring_directive(":avocado: enable\n:avocado: tags=fast", 'enable'))
        self.assertFalse(check_docstring_directive(":AVOCADO: ENABLE", 'enable'))
        self.assertFalse(check_docstring_directive(":avocado: enabled", 'enable'))

    def test_disabled(self):
        self.assertTrue(check_docstring_directive(":avocado: disable", 'disable'))
        self.assertTrue(check_docstring_directive(":avocado:\tdisable", 'disable'))
        self.assertFalse(check_docstring_directive(":AVOCADO: DISABLE", 'disable'))
        self.assertFalse(check_docstring_directive(":avocado: disabled", 'disable'))

    def test_get_tags_empty(self):
        for tag in self.NO_TAGS:
            self.assertEqual({}, get_docstring_directives_tags(tag))

    def test_tag_single(self):
        raw = ":avocado: tags=fast"
        exp = {"fast": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_double(self):
        raw = ":avocado: tags=fast,network"
        exp = {"fast": None, "network": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_double_with_empty(self):
        raw = ":avocado: tags=fast,,network"
        exp = {"fast": None, "network": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_lowercase_uppercase(self):
        raw = ":avocado: tags=slow,DISK"
        exp = {"slow": None, "DISK": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_duplicate(self):
        raw = ":avocado: tags=SLOW,disk,disk"
        exp = {"SLOW": None, "disk": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_tab_separator(self):
        raw = ":avocado:\ttags=FAST"
        exp = {"FAST": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_empty(self):
        raw = ":avocado: tags="
        exp = {}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_newline_before(self):
        raw = ":avocado: enable\n:avocado: tags=fast"
        exp = {"fast": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_newline_after(self):
        raw = ":avocado: tags=fast,slow\n:avocado: enable"
        exp = {"fast": None, "slow": None}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_keyval_single(self):
        raw = ":avocado: tags=fast,arch:x86_64"
        exp = {"fast": None, "arch": set(["x86_64"])}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_keyval_double(self):
        raw = ":avocado: tags=fast,arch:x86_64,arch:ppc64"
        exp = {"fast": None, "arch": set(["x86_64", "ppc64"])}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_tag_keyval_duplicate(self):
        raw = ":avocado: tags=fast,arch:x86_64,arch:ppc64,arch:x86_64"
        exp = {"fast": None, "arch": set(["x86_64", "ppc64"])}
        self.assertEqual(get_docstring_directives_tags(raw), exp)

    def test_get_requirement_empty(self):
        for req in self.NO_REQS:
            self.assertEqual([], get_docstring_directives_requirements(req))

    def test_requirement_single(self):
        raw = ":avocado: requirement={\"foo\":\"bar\"}"
        exp = [{"foo": "bar"}]
        self.assertEqual(get_docstring_directives_requirements(raw), exp)

    def test_requirement_double(self):
        raw = ":avocado: requirement={\"foo\":\"bar\"}\n:avocado: requirement={\"uri\":\"http://foo.bar\"}"
        exp = [{"foo": "bar"}, {"uri": "http://foo.bar"}]
        self.assertEqual(get_docstring_directives_requirements(raw), exp)

    def test_directives_regex(self):
        """
        Tests the regular expressions that deal with docstring directives
        """
        for directive in self.VALID_DIRECTIVES:
            self.assertTrue(DOCSTRING_DIRECTIVE_RE.match(directive))
        for directive in self.INVALID_DIRECTIVES:
            self.assertFalse(DOCSTRING_DIRECTIVE_RE.match(directive))
