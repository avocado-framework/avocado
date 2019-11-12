avocado.utils.gdb
=================

The :mod:`avocado.utils.gdb` APIs that allows a test to interact with
GDB, including setting a executable to be run, setting breakpoints
or any other types of commands. This requires a test written with
that approach and API in mind.

.. tip:: Even though this section describes the use of the Avocado GDB
   features, it's also possible to debug some application offline by
   using tools such as `rr <http://rr-project.org>`_.  Avocado ships
   with an example wrapper script (to be used with ``--wrapper``) for
   that purpose.

APIs
----

Avocado's GDB module, provides three main classes that lets a test writer
interact with a `gdb` process, a `gdbserver` process and also use the GDB
remote protocol for interaction with a remote target.

Please refer to :mod:`avocado.utils.gdb` for more information.

Example
~~~~~~~

Take a look at ``examples/tests/modify_variable.py`` test::

    def test(self):
        """
        Execute 'print_variable'.
        """
        path = os.path.join(self.workdir, 'print_variable')
        app = gdb.GDB()
        app.set_file(path)
        app.set_break(6)
        app.run()
        self.log.info("\n".join(app.read_until_break()))
        app.cmd("set variable a = 0xff")
        app.cmd("c")
        out = "\n".join(app.read_until_break())
        self.log.info(out)
        app.exit()
        self.assertIn("MY VARIABLE 'A' IS: ff", out)

This allows us to automate the interaction with the GDB in means of
setting breakpoints, executing commands and querying for output.

When you check the output (``--show=test``) you can see that despite
declaring the variable as 0, ff is injected and printed instead.
