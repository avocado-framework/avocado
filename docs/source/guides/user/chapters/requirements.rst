.. _managing-requirements:

Managing Requirements
=====================

.. note:: Test requirements are supported only on the nrunner runner. To use
  this feature, remember to use `--test-runner=nrunner` argument.

A test's requirement can be fulfilled by the Requirements Resolver feature.

Test's requirements are specified in the test definition and are fulfilled
based on the supported requirement `type`.

Test workflow with requirements
-------------------------------

When a requirement is defined for a test, it is marked as a dependency for that
test. The test will wait for all the requirements to complete successfully before
it is started.

When any of the requirements defined on a test fails, the test is skipped.

Defining a test requirement
---------------------------

A test requirement is described in the JSON format. Following is an example of
a requirement of `type` `package`::

        {"type": "package", "name": "hello"}

To define a requirement for the test, use the test's docstring with the format of
keywords `:avocado: requirement=`. The following example shows the same package
requirement showed above inside a test docstring::

        from avocado import Test


        class PassTest(Test):
            """
            :avocado: requirement={"type": "package", "name": "hello"}
            """
            def test(self):
                """
                A success test
                """

It is possible to define multiple requirements for a test. Following is an
example using more than one requirement definition::

        from avocado import Test


        class PassTest(Test):
            """
            :avocado: requirement={"type": "package", "name": "hello"}
            :avocado: requirement={"type": "package", "name": "bash"}
            """
            def test(self):
                """
                A success test
                """

Defining a requirement in the class docstring will fulfill the requirement for
every test within a test class. Defining a requirement in the test docstring
will fulfill the requirement for that single test only.

Supported types of requirements
-------------------------------

The following `types` of requirements are supported:

Package
+++++++

Support managing of packages using the Avocado Software Manager utility. The
parameters available to use the package `type` of requirements are:

 * `type`: `package`
 * `name`: the package name (required)
 * `action`: one of `install`, `check`, or `remove`
   (optional, defaults to `install`)

Following is an example of a test using the Package requirement:

.. literalinclude:: ../../../../../examples/tests/passtest_with_requirement.py
