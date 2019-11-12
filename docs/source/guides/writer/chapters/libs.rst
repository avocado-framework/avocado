.. _utility-libraries:

Utility Libraries
=================

Avocado gives to you more than 40 Python utility libraries (so far), that can
be found under the :mod:`avocado.utils`. You can use these libraries to avoid
having to write necessary routines for your tests. These are very general in
nature and can help you speed up your test development.

The utility libraries may receive incompatible changes across minor versions,
but these will be done in a staged fashion. If a given change to an utility
library can cause test breakage, it will first be documented and/or deprecated,
and only on the next subsequent minor version it will actually be changed.

What this means is that upon updating to later minor versions of Avocado, you
should look at the Avocado Release Notes for changes that may impact your
tests.

.. seealso:: If you would like a detailed API reference of this libraries,
  please visit the "Reference API" section on the left menu.

The following pages are the documentation for some of the Avocado utilities:

.. warning:: TODO: Looks like the utils libraries documentation will be mainly
  on docstrings, right?  If so, maybe makes sense to have only documented on API
  reference? And any general instruction would be on module docstring. What you
  guys think?

.. toctree::
   :maxdepth: 1

   ../libs/gdb
   ../libs/vmimage
