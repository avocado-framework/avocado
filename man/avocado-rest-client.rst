:title: avocado-rest-client
:subtitle: REST client command line tool
:title_upper: AVOCADO
:manual_section: 1

SYNOPSIS
========

avocado-rest-client [-h] [--hostname HOSTNAME] [--port PORT] [--username USERNAME] [--password PASSWORD]

DESCRIPTION
===========

Avocado is a modern test framework that is built on the experience
accumulated with `autotest` (`http://autotest.github.io`).

`avocado-rest-client` is the name of the command line tool that interacts
with `avocado-server`.

`avocado-server` (`http://github.com/avocado-framework/avocado-server`)
is an HTTP server that provides an REST API for results job results and
other features.

For more information about the Avocado project, please check its website:
http://avocado-framework.github.io/

OPTIONS
=======

The following list of options are builtin, application level `avocado-rest-client`
options. Most other options are implemented via plugins and will depend
on them being loaded::

 --hostname HOSTNAME  Hostname or IP address for the avocado server
 --port PORT          Port where avocado server is listening on
 --username USERNAME  Username to authenticate to avocado server
 --password PASSWORD  Password to give to avocado server

Real use of avocado depends on running avocado subcommands. This the current list
of subcommands::

   server             inspects the server status and available functionality

To get usage instructions for a given subcommand, run it with `--help`. Example::

 $ avocado-rest-client server --help

  -l, --list-brief     list all records briefly
  -s, --status         shows the avocado-server status

FILES
=====

::

 /etc/avocado/avocado.conf
    system wide configuration file

BUGS
====

If you find a bug, please report it over our github page as an issue.

LICENSE
================

Avocado is released under GPLv2 (explicit version)
`http://gnu.org/licenses/gpl-2.0.html`. Even though most of the current code is
licensed under a "and any later version" clause, some parts are specifically
bound to the version 2 of the license and therefore that's the official license
of the prject itself. For more details, please see the LICENSE file in the
project source code directory.

MORE INFORMATION
================

For more information please check Avocado's project website, located at
`http://avocado-framework.github.io/`. There you'll find links to online
documentation, source code and community resources.

AUTHOR
======

Avocado Development Team <avocado-devel@redhat.com>
