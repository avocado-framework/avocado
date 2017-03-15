.. _about-avocado:

.. Note: this section section shares content with the project README
         file.  When editing this section, also sync the content with
         the README file.  Also notice that this file uses a larger
         set of ReST/sphinx statements, which do not look as good on a
         plain README file.

About Avocado
=============

Avocado is a set of tools and libraries to help with automated testing.

One can call it a test framework with benefits.  Native tests are
written in Python and they follow the :mod:`unittest` pattern, but any
executable can serve as a test.

Avocado is composed of:

* A test runner that lets you execute tests. Those tests can be either
  written in your language of choice, or be written in Python and use
  the available libraries. In both cases, you get facilities such as
  automated log and system information collection.

* Libraries that help you write tests in a concise, yet expressive and
  powerful way.  You can find more information about what libraries
  are intended for test writers at :ref:`libraries-apis`.

* :mod:`Plugins <avocado.plugins>` that can extend and add new functionality
  to the Avocado Framework.

Avocado is built on the experience accumulated with `Autotest
<http://autotest.github.io/>`__, while improving on its weaknesses and
shortcomings.

Avocado tries as much as possible to comply with standard Python testing
technology. Tests written using the Avocado API are derived from the unittest
class, while other methods suited to functional and performance testing were
added. The test runner is designed to help people to run their tests while
providing an assortment of system and logging facilities, with no effort,
and if you want more features, then you can start using the API features
progressively.
