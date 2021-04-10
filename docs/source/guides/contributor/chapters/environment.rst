Development environment
=======================

.. include:: /.include/helpus.rst

.. warning:: TODO: Needs improvment here. i.e: virtualenvs, GPG, etc.

Installing dependencies
-----------------------

You need to install few dependencies before start coding::

 $ sudo dnf install gcc libvirt-devel


Installing in develop mode
--------------------------

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
for example "avocado-vt". These also need to be deployed and "linked" in order
to work properly with the Avocado from sources (installed version works out of
the box).

You can install external plugins as you wish, and/or according to the
specific plugin's maintainer recommendations.

Plugins that are developed by the Avocado team, will try to follow the
same Setuptools standard for distributing the packages. Because of that,
as a facility, you can use `make requirements-plugins` from the main
Avocado project to install requirements of the plugins and `make
develop-external` to install plugins in develop mode to. You just need
to set where your plugins are installed, by using the environment
variable `$AVOCADO_EXTERNAL_PLUGINS_PATH`. The workflow could be::

    $ cd $AVOCADO_PROJECTS_DIR
    $ git clone $AVOCADO_GIT
    $ git clone $AVOCADO_PROJECT2
    $ # Add more projects
    $ cd avocado    # go into the main Avocado project dir
    $ make requirements-plugins
    $ export AVOCADO_EXTERNAL_PLUGINS_PATH=$AVOCADO_PROJECTS_DIR
    $ make develop-external

You should see the process and status of each directory.
