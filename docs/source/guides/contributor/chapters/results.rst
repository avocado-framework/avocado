Implementing other result formats
---------------------------------

If you are looking to implement a new machine or human readable output
format, you can refer to :mod:`avocado.plugins.xunit` and use it as a
starting point.

If your result is something that is produced at once, based on the
complete job outcome, you should create a new class that inherits from
:class:`avocado.core.plugin_interfaces.Result`  and implements the
:meth:`avocado.core.plugin_interfaces.Result.render` method.

But, if your result implementation is something that outputs
information live before/during/after tests, then the
:class:`avocado.core.plugin_interfaces.ResultEvents` interface is the
one to look at.  It will require you to implement the methods that
will perform actions (write to a file/stream) for each of the defined
events on a Job and test execution.

You can take a look at `Plugins` for more information on how to
write a plugin that will activate and execute the new result format.
