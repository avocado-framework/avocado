Development environment
=======================

.. include:: /.include/helpus.rst

.. warning:: TODO: Needs improvment here. i.e: virtualenvs, GPG, etc.

Since version 0.31.0, our plugin system requires Setuptools entry points to be
registered. If you're hacking on Avocado and want to use the same, possibly
modified, source for running your tests and experiments, you may do so with one
additional step::

  $ make develop

On POSIX systems this will create an "egg link" to your original source tree under
"$HOME/.local/lib/pythonX.Y/site-packages". Then, on your original source tree, an
"egg info" directory will be created, containing, among other things, the Setuptools
entry points mentioned before. This works like a symlink, so you only need to run
this once (unless you add a new entry-point, then you need to re-run it to make it
available).

Avocado supports various plugins, which are distributed as separate projects,
for example "avocado-vt" and "avocado-virt". These also need to be
deployed and linked in order to work properly with the Avocado from
sources (installed version works out of the box). To simplify this you can
use `make requirements-plugins` from the main Avocado project to install
requirements of the plugins and `make link` to link and develop the
plugins. The workflow could be::

    $ cd $AVOCADO_PROJECTS_DIR
    $ git clone $AVOCADO_GIT
    $ git clone $AVOCADO_PROJECT2
    $ # Add more projects
    $ cd avocado    # go into the main Avocado project dir
    $ make requirements-plugins
    $ make link

You should see the process and status of each directory.
