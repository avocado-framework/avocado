==================
 Optional Plugins
==================

This is where plugins shipped with Avocado, but not considered core
functionality can be found.

To try them out on a development environment, you may run::

 $ pip install -e optional_plugins/<plugin-name>

For example::

 $ pip install -e optional_plugins/html
 $ pip install -e optional_plugins/ansible

And to remove them on a development environment, you may run::

 $ pip uninstall <plugin-package-name>

For example::

 $ pip uninstall avocado-framework-plugin-result-html
 $ pip uninstall avocado-framework-plugin-ansible

Also, on a development environment, the following command from the
topmost Avocado source code directory will enable all optional
plugins::

 $ make develop-plugins

And to enable a specific plugin::

 $ make develop-plugin PLUGIN=html
