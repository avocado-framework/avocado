=================
 Plugin Examples
=================

Here you can find a collection of example code for the various Avocado
Plugin interfaces.

To try them out on a development environment, you may run::

 $ cd <plugin-type>/<plugin-example>
 $ python setup.py develop --user

And to remove them on a development environment, you may run, at the
same directory::

 $ python setup.py develop --uninstall --user

Second way to add to install plugin is to use Makefile's link target,
Simply add symlink of target plugin to parent avocado directory and
do make link::
 $ ln -s examples/plugins/job-pre-post/mail ../mail-plugin
 $ make link
