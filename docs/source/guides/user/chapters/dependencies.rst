.. _managing-requirements:

Managing Dependencies
=====================

.. note:: Test dependencies are supported only on the nrunner runner.

A test's dependency can be fulfilled by the Dependencies Resolver feature.

Test's dependencies are specified in the test definition and are fulfilled
based on the supported dependency `type`.

Test workflow with dependencies
-------------------------------

When a dependency is defined for a test, it is marked as a dependency for that
test. The test will wait for all the dependencies to complete successfully before
it is started.

When any of the dependencies defined on a test fails, the test is skipped.

When the dependency is fulfilled, its metadata will be saved into the avocado cache, so
avocado will be able to reuse it in another tests.

Also, the dependency metadata will stay in cache after the Avocado run, so the second
run of the tests will use dependencies from cache, which will make tests more
efficient. If you want to know the state of cache, you can use cache interface
with `avocado cache list`.

.. warning::

   `avocado cache` interface works only with metadata about dependencies. Any manipulation
   with `avocado cache` interface doesn't affects the real data stored in the environment.


.. warning::

        If any environment is modified without Avocado knowing about it 
        (packages being uninstalled, podman images removed, etc), the 
        dependency metadata in cache won't be updated, because of this, the resolution
        behavior is undefined and will probably crash.
        If such a change is made to the environment, it's recommended to clear 
        the dependencies cache file.

Defining a test dependency
---------------------------

A test dependency is described in the JSON format. Following is an example of
a dependency of `type` `package`::

        {"type": "package", "name": "hello"}

To define a dependency for the test, use the test's docstring with the format of
keywords ``:avocado: dependency=``. The following example shows the same package
dependency showed above inside a test docstring::

        from avocado import Test


        class PassTest(Test):
            """
            :avocado: dependency={"type": "package", "name": "hello"}
            """
            def test(self):
                """
                A success test
                """

It is possible to define multiple dependencies for a test. Following is an
example using more than one dependency definition::

        from avocado import Test


        class PassTest(Test):
            """
            :avocado: dependency={"type": "package", "name": "hello"}
            :avocado: dependency={"type": "package", "name": "bash"}
            """
            def test(self):
                """
                A success test
                """

Defining a dependency in the class docstring will fulfill the dependency for
every test within a test class. Defining a dependency in the test docstring
will fulfill the dependency for that single test only.

Supported types of dependencies
-------------------------------

The following `types` of dependencies are supported:

Package
+++++++

Support managing of packages using the Avocado Software Manager utility. The
parameters available to use the package `type` of dependencies are:

 * `type`: `package`
 * `name`: the package name (required)
 * `action`: one of `install`, `check`, or `remove`
   (optional, defaults to `install`)

Following is an example of a test using the Package dependency:

.. literalinclude:: ../../../../../examples/tests/passtest_with_dependency.py

Asset
+++++

Support fetching assets using the Avocado Assets utility. The
parameters available to use the asset `type` of dependencies are:

 * `type`: `asset`
 * `name`: the file name or uri (required)
 * `asset_has`: hash of the file (optional)
 * `algorithm`: hash algorithm (optional)
 * `locations`: location(s) where the file can be fetched from (optional)
 * `expire`: time in seconds for the asset to expire (optional)

Podman Image
++++++++++++

Support pulling podman images ahead of test execution time.  This
should only be used explicitly if a test interacts with ``podman``
directly, say by executing containers on its own.  If you are using
the ``podman`` spawner (``--spawner=podman``) this will have no
effect on the spawner.

 * `type`: `podman-image`
 * `uri`: the image reference, in any format supported by ``podman
   pull`` itself.

Ansible Module
++++++++++++++

If you install the Ansible plugin
(``avocado-framework-plugin-ansible`` from PIP or
``python3-avocado-plugins-ansible`` from RPM packages), you will will
be able to use the ``ansible-module`` dependency.

 * `type`: `ansible-module`
 * `uri`: the name of the ansible module.

All other arguments will be treated as arguments to the ansible modules.

Following is an example of tests using ansible's ``file`` and ``user``
modules:

.. literalinclude:: ../../../../../examples/tests/dependency_ansible.py
