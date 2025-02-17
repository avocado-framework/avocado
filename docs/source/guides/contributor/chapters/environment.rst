Development environment
=======================

Using a container
-----------------

Having reproducible development environments is hard because
developers will usually choose their preferred environments, and those
will never be the same for two people.  Using a container can be a
good option if you're unsure whether your development environment is
sound or compatible enough.

The Avocado project maintains a container image that can serve as a
pretty good starting point for development too (it's actually intended
to be used on some CI checks, but don't mind that).  You can pull the
image from::

    quay.io/avocado-framework/avocado-ci-fedora-40

It's a simple image, with just a number of known needed packages
installed.  This is the full definition of the image:

.. literalinclude:: ../../../../../contrib/containers/ci/selftests/fedora-40.docker

You can use the information there to apply to your own environment if
you choose not to use the container image itself.

Installing dependencies
-----------------------

You need to install few dependencies before start coding::

 $ sudo dnf install gcc python-devel enchant

Then install all the python dependencies::

 $ make requirements-dev

Or if you already have pip installed, you can run directly::

 $ pip install -r requirements-dev.txt

If you intend to build the documentation locally, please also run::

 $ pip install -r requirements-doc.txt

Installing in develop mode
--------------------------

Since version 0.31.0, our plugin system requires Setuptools entry points to be
registered. If you're hacking on Avocado and want to use the same, possibly
modified, source for running your tests and experiments, you may do so with one
additional step::

  $ python3 setup.py develop [--user]

On POSIX systems this will create an "egg link" to your original source tree under
``$HOME/.local/lib/pythonX.Y/site-packages``. Then, on your original source tree, an
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
as a facility, you can use ``make requirements-plugins`` from the main
Avocado project to install requirements of the plugins and ``make
develop-external`` to install plugins in develop mode to. You just need
to set where your plugins are installed, by using the environment
variable ``$AVOCADO_EXTERNAL_PLUGINS_PATH``. The workflow could be::

    $ cd $AVOCADO_PROJECTS_DIR
    $ git clone $AVOCADO_GIT
    $ git clone $AVOCADO_PROJECT2
    $ # Add more projects
    $ cd avocado    # go into the main Avocado project dir
    $ make requirements-plugins
    $ export AVOCADO_EXTERNAL_PLUGINS_PATH=$AVOCADO_PROJECTS_DIR
    $ make develop-external

You should see the process and status of each directory.

GPG Signatures
--------------

This is an optional step for most contributors, but if you're
interested in ensuring that your contribution is linked to yourself,
this is the best way to do so.

To get a GPG signature, you can find many howtos on the internet, but
it generally works like this::

    $ gpg --gen-key  # defaults are usually fine (using expiration is recommended)
    $ gpg --send-keys $YOUR_KEY    # to propagate the key to outer world

Then, you should enable it in git::

    $ git config --global user.signingkey $YOUR_KEY

Optionally, you can link the key with your GH account:

1. Login to github
2. Go to settings->SSH and GPG keys
3. Add New GPG key
4. run ``$(gpg -a --export $YOUR_EMAIL)`` in shell to see your key
5. paste the key there
