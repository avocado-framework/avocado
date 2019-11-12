Writing an Avocado plugin
-------------------------

What better way to understand how an Avocado plugin works than creating one?
Let's use another old time favorite for that, the "Print hello world" theme.

Code example
~~~~~~~~~~~~

Let's say you want to write a plugin that adds a new subcommand to the test
runner, ``hello``. This is how you'd do it::

    from avocado.core.output import LOG_JOB
    from avocado.core.plugin_interfaces import CLICmd


    class HelloWorld(CLICmd):

        name = 'hello'
        description = 'The classical Hello World! plugin example.'

        def run(self, args):
            LOG_JOB.info(self.description)

As you can see, this plugins inherits from
:class:`avocado.core.plugin_interfaces.CLICmd`.  This specific base class
allows for the creation of new commands for the Avocado CLI tool. The only
mandatory method to be implemented is :func:`run
<avocado.core.plugin_interfaces.CLICmd.run>` and it's the plugin main entry
point.

This plugin uses :py:data:`avocado.core.output.LOG_JOB` to produce the hello
world output in the Job log. One can also use
:py:data:`avocado.core.output.LOG_UI` to produce output in the human readable
output.

Registering Plugins
~~~~~~~~~~~~~~~~~~~

Avocado makes use of the `setuptools` and its `entry points` to register and
find Python objects. So, to make your new plugin visible to Avocado, you need
to add to your setuptools based `setup.py` file something like::

 setup(name='mypluginpack',
 ...
 entry_points={
    'avocado.plugins.cli': [
       'hello = mypluginpack.hello:HelloWorld',
    ]
 }
 ...

Then, by running either ``$ python setup.py install`` or ``$ python setup.py
develop`` your plugin should be visible to Avocado.

Namespace
~~~~~~~~~

The plugin registry mentioned earlier, (`setuptools` and its `entry points`) is
global to a given Python installation.  Avocado uses the namespace prefix
``avocado.plugins.`` to avoid name clashes with other software.  Now, inside
Avocado itself, there's no need keep using the ``avocado.plugins.`` prefix.

Take for instance, the Job Pre/Post plugins are defined on ``setup.py``::

  'avocado.plugins.job.prepost': [
     'jobscripts = avocado.plugins.jobscripts:JobScripts'
  ]

The setuptools entry point namespace is composed of the mentioned prefix
``avocado.plugins.``, which is is then followed by the Avocado plugin type, in
this case, ``job.prepost``.

Inside Avocado itself, the fully qualified name for a plugin is the plugin
type, such as ``job.prepost`` concatenated to the name used in the entry point
definition itself, in this case, ``jobscripts``.

To summarize, still using the same example, the fully qualified Avocado plugin
name is going to be ``job.prepost.jobscripts``.
