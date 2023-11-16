================
Standard plugins
================

Avocado is highly modular, and a lot of its functionality is
implemented as "plugins".  On this section, you'll find documentation
for plugins that come standard with Avocado.

Please note that this is not a fully comprehensive list.

.. tip:: Running ``avocado plugins`` will show the full list of
         plugins installed and available on your system.


.. toctree::
   :maxdepth: 3

   standard/teststmpdir

================
Optional plugins
================

The plugins listed here are not automatically available on every
Avocado installation.  Depending on the installation method, it may
require additional steps or packages to be installed.

Some of these plugins may have extra dependencies of their own.

.. toctree::
   :maxdepth: 3

   optional/avocado_classless
   optional/golang
   optional/results/index
   optional/robot
   optional/varianters/index
   optional/varianter_pict
   optional/multiplexer
   optional/varianter_yaml_to_mux
