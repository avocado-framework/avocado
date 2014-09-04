.. _about-avocado:

About Avocado
=============

Avocado is a set of tools and libraries (what people call these days a framework)
to perform automated testing.

Avocado is composed by:

* Programs that let you run tests. Those tests can be either written on your
  language of choice, or use the python API available. In both cases, you get
  facilities such as automated log and system information collection.

* APIs that help you write tests in a concise, yet expressive way.

Avocado tries as much as possible to comply with standard python testing
technology. Tests written using the avocado API are derived from the unittest
class, while other methods suited to functional and performance testing were
added. The test runner is designed to help people to run their tests while
providing an assortment of system and logging facilities, with no effort,
and if you want more features, then you can start using the API features
progressively.

An `extensive set of slides about avocado
<https://docs.google.com/presentation/d/1PLyOcmoYooWGAe-rS2gtjmrZ0B9J22FbfpNlQY8fIUE>`__,
including details about its architecture, main features and status is available
in google-drive.
