.. _yaml_loader:

YAML Loader (yaml_loader)
=========================

This plugin is related to `Yaml_to_mux` plugin and it understands the same
content, only it works on loader-level, rather than on test variants level.
The result is that this plugin tries to open the test reference as if it was
a file specifying variants and if it succeeds it iterates through variants
and looks for `test_reference` entries. On success it attempts to discover
the reference using either loader defined by `test_reference_resolver_class`
or it fall-backs to `FileLoader` when not specified. Then it assigns the
current variant's params to all of the discovered tests. This way one can
freely assign various variants to different tests.

Keep in mind YAML files (in Avocado) are ordered, therefor variant name won't
re-arrange the test order. The only exception is when you use the same variant
name twice, then the second one will get merged into the first one.

Also note that in case of no `test_reference` or just when no tests are
discovered in the current variant, there is no error, no warning and
the loader reports the discovered tests (if any) without the variant
which did not produced any tests.

The simplest way to learn about this plugin is to look at examples in
``examples/yaml_to_mux_loader/``.
