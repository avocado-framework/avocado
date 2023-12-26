distro
======

Avocado has some planned features that depend on knowing the Linux
Distribution being used on the system. The most basic command prints the
detected Linux Distribution::

    $ avocado distro
    Detected distribution: fedora (x86_64) version 39 release 0

Other features are available with the same command when command line
options are given, as shown by the `--help` option.

For instance, it possible to create a so-called "Linux Distribution
Definition" file, by inspecting an installation tree. The installation
tree could be the contents of the official installation ISO or a local
network mirror.

These files let Avocado pinpoint if a given installed package is part of
the original Linux Distribution or something else that was installed
from an external repository or even manually. This, in turn, can help
detecting regressions in base system packages that affected a given test
result.

To generate a definition file run::

    $ avocado distro --distro-def-create --distro-def-name avocadix  \
                     --distro-def-version 1 --distro-def-arch x86_64 \
                     --distro-def-type rpm --distro-def-path /mnt/dvd

And the output will be something like::

    Loading distro information from tree... Please wait...
    Distro information saved to "avocadix-1-x86_64.distro"
