Other Resources
===============

Open Source Projects Relying on Avocado
---------------------------------------

The following is a partial list of projects that use Avocado as either
the framework for their tests, or the Avocado test runner to run other
regular tests.

Fedora Modularity
~~~~~~~~~~~~~~~~~

The `Fedora Modularity <https://github.com/fedora-modularity>`__
project is about building a modular Linux OS with multiple versions of
components on different lifecycles.

It uses Avocado in its `meta test family
<https://github.com/fedora-modularity/meta-test-family>`__ subproject.

QEMU
~~~~

`QEMU <https://www.qemu.org/>`__ is a generic and open source machine
emulator and virtualizer.

It uses Avocado in `functional level tests
<https://qemu-project.gitlab.io/qemu/devel/testing.html#acceptance-tests-using-the-avocado-framework>`__.

SoS
~~~

`SoS <https://github.com/sosreport/sos>`__ is an extensible, portable,
support data collection tool primarily aimed at Linux distributions
and other UNIX-like operating systems.

It uses Avocado in its `functional level tests
<https://github.com/sosreport/sos/blob/fc0ae513b1630ecea96d89af1952d384995a3257/tests/sos_tests.py#L56>`__.

DAOS
~~~~

The `Distributed Asynchronous Object Storage (DAOS)
<https://daos-stack.github.io/>`__ is an open-source object store
designed from the ground up for massively distributed Non Volatile
Memory (NVM).

It uses Avocado in its `ftest
<https://github.com/daos-stack/daos/blob/master/src/tests/ftest/avocado_tests.py>`__
test suite.

RUDDER
~~~~~~

`RUDDER <https://www.qemu.org/>`__ is a European, open source and
multi-platform solution allowing you to manage configurations and
compliance of your systems.

It uses Avocado in its `ncf <https://github.com/Normation/ncf>`__
project, which is a framework that runs in pure CFEngine language, to
help structure your CFEngine policy and provide reusable, single
purpose components.

POK
~~~

`POK <https://pok-kernel.github.io/>`__ is a real-time embedded
operating system for safety-critical systems.

It uses Avocado in its `unitary
<https://github.com/pok-kernel/pok/tree/main/testsuite/unitary_tests>`__
and `multiprocessing unitary
<https://github.com/pok-kernel/pok/tree/main/testsuite/multiprocessing_unitary_tests>`__
tests.

isar
~~~~

`isar <https://github.com/ilbers/isar>`__ is the "Integration System
for Automated Root filesystem generation".  It is a set of scripts for
building software packages and repeatable generation of Debian-based
root filesystems with customizations.

It is used in the project's `test suite
<https://github.com/ilbers/isar/tree/master/testsuite#install-avocado>`__.

Avocado extensions
------------------

The following are extensions of the Avocado framework specifically
designed to enhance Avocado with more targeted testing capabilities.

Avocado-VT
~~~~~~~~~~

`Avocado-VT <https://github.com/avocado-framework/avocado-vt>`__ lets
you execute virtualization related tests (then known as virt-test),
with all conveniences provided by Avocado.

Together with its various test providers (`QEMU
<https://github.com/autotest/tp-qemu>`__, `LibVirt
<https://github.com/autotest/tp-libvirt>`__) it provides literally
dozens of thousands of virtualization related tests.

Avocado-I2N
~~~~~~~~~~~

`Avocado-I2N <https://github.com/intra2net/avocado-i2n>`__ is a plugin
that extends Avocado-VT with automated vm state setup, inheritance,
and traversal.

Avocado-cloud
~~~~~~~~~~~~~

`Avocado-cloud <https://github.com/virt-s1/avocado-cloud>`__ is a
cloud test suite for RHEL guests on various clouds such as Alibaba,
AWS, Azure, Huawei, IBM Cloud and OpenStack.

Test specific repositories
~~~~~~~~~~~~~~~~~~~~~~~~~~

These repositories contain a multitude of tests for specific different
purposes.

* `Avocado Misc Tests <https://github.com/avocado-framework-tests/avocado-misc-tests>`__: a repository dedicated to host tests initially ported from autotest client tests repository, but not limited to those.

* `OpenPOWER Host OS and Guest Virtual Machine (VM) stability tests <https://github.com/open-power-host-os/tests>`__

Presentations
-------------

This is a collection of some varied Avocado related presentations on
the web:

* `Testing Framework Internals (DevConf 2017) <https://www.youtube.com/watch?v=--fxmmJ5SBA&list=PLpLgrCSz067ao8NsOHdaYtq-06SmBMOBR>`__
* `Auto Testing for AArch64 Virtualization (Linaro connect San Francisco 2017) <http://connect.linaro.org/resource/sfo17/sfo17-502/>`__
* `libvirt integration and testing for enterprise KVM/ARM (Linaro Connect Budapest 2017) <http://connect.linaro.org/resource/bud17/bud17-213/>`__
* `Automated Testing Framework (PyCon CZ 2016) <https://www.youtube.com/watch?v=eTR-LvW80pM&list=PLpLgrCSz067ao8NsOHdaYtq-06SmBMOBR&index=2>`__
* `Avocado and Jenkins (DevConf 2016) <https://www.youtube.com/watch?v=XJ7IWQflM9g&list=PLpLgrCSz067ao8NsOHdaYtq-06SmBMOBR&index=4>`__
* `Avocado: Next Gen Testing Toolbox (DevConf 2015) <https://www.youtube.com/watch?v=xMXS7NB4WSs&index=5&list=PLpLgrCSz067ao8NsOHdaYtq-06SmBMOBR>`__
* Avocado workshop (DevConf 2015) `mindmap with all commands/content <https://www.mindmeister.com/504616310/avocado-workshop>`__ and `a partial video <https://www.mindmeister.com/504616310/avocado-workshop>`__
* `Avocado: Open Source Testing Made Easy (LinuxCon 2015) <https://www.youtube.com/watch?v=tdEg07BfdBw&index=3&list=PLpLgrCSz067ao8NsOHdaYtq-06SmBMOBR>`__
