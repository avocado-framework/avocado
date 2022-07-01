.. _managing-requirements:

Managing Requirements
=====================

.. note:: Test requirements are supported only on the nrunner runner.

A test's requirement can be fulfilled by the Requirements Resolver feature.

Test's requirements are specified in the test definition and are fulfilled
based on the supported requirement `type`.

Test workflow with requirements
-------------------------------

When a requirement is defined for a test, it is marked as a dependency for that
test. The test will wait for all the requirements to complete successfully before
it is started.

When any of the requirements defined on a test fails, the test is skipped.

When the requirement is fulfilled, it will be saved into the avocado cache, and
it will be reused by other tests.

Also, the requirement will stay in cache after the Avocado run, so the second
run of the tests will use requirements from cache, which will make tests more
efficient.

.. warning::

        If any environment is modified without Avocado knowing about it 
        (packages being uninstalled, podman images removed, etc), the 
        requirement resolution behavior is undefined and will probably crash. 
        If such a change is made to the environment, it's recommended to clear 
        the requirements cache file.

Defining a test requirement
---------------------------

A test requirement is described in the JSON format. Following is an example of
a requirement of `type` `package`::

        {"type": "package", "name": "hello"}

To define a requirement for the test, use the test's docstring with the format of
keywords ``:avocado: requirement=``. The following example shows the same package
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

Asset
+++++

Support fetching assets using the Avocado Assets utility. The
parameters available to use the asset `type` of requirements are:

 * `type`: `asset`
 * `name`: the file name or uri (required)
 * `asset_has`: hash of the file (optional)
 * `algorithm`: hash algorithm (optional)
 * `locations`: location(s) where the file can be fetched from (optional)
 * `expire`: time in seconds for the asset to expire (optional)

