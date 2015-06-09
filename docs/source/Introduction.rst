.. _about-avocado:

About Avocado
=============

Avocado is a set of tools and libraries to help with automated testing.

One can call it a test framework with benefits. Native tests are
written in Python and they follow the :mod:`unittest` pattern, but any
executable can serve as a test.

Avocado is composed by:

* A test runner that lets you execute tests. Those tests can be either written in your
  language of choice, or use the Python API available. In both cases, you get
  facilities such as automated log and system information collection.

* APIs that help you write tests in a concise, yet expressive way.
  The Test API is the whole set of modules, classes and functions available
  under the :mod:`avocado` main module, excluding the :mod:`avocado.core`
  module and their submodules, which is part of application's infrastructure.

* :mod:`Plugins <avocado.core.plugins>` that can extend and add new functionality
  to the Avocado Framework.

Avocado tries as much as possible to comply with standard Python testing
technology. Tests written using the Avocado API are derived from the unittest
class, while other methods suited to functional and performance testing were
added. The test runner is designed to help people to run their tests while
providing an assortment of system and logging facilities, with no effort,
and if you want more features, then you can start using the API features
progressively.

An `extensive set of slides about Avocado
<https://docs.google.com/presentation/d/1PLyOcmoYooWGAe-rS2gtjmrZ0B9J22FbfpNlQY8fIUE>`__,
including details about its architecture, main features and status is available
in google-drive. Mindmap from workshop (2015) demonstrating features on
examples available `here <https://www.mindmeister.com/504616310>`__.
