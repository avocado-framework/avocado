==================
 Optional Plugins
==================

This is where plugins shipped with Avocado, but not considered core
functionality can be found.

To try them out on a development environment, you may run::

 $ cd <plugin-dir>/
 $ python setup.py develop --user

And to remove them on a development environment, you may run, at the
same directory::

 $ python setup.py develop --uninstall --user

Also, on a development environment, the following command on the
topmost Avocado source code directory will enable all optional
plugins::

 $ make link

And this will disable all optional plugins::

 $ make unlink
