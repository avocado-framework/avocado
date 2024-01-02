=====================
Remote Spawner Plugin
=====================

This plugin makes use of remote `aexpect
<https://github.com/avocado-framework/aexpect/>`__ sessions (to remote
hosts or equivalently remote containers behind remote hosts forwarded
via specific ports) as slots to schedule test runs on.

It mainly draws inspiration and mimics slot and other
code from the LXC spawner with the exception of extra configurable
test timeout that is enforced by aexpect as a dependency and fully
specific to this type of spawner.

To install the Remote Spawner plugin from pip, use::

    $ sudo pip install avocado-framework-plugin-spawner-remote

After it is installed, add a slot (e.g. "board") to your avocado
config file::

    [spawner.remote]
    slots = ['board']

Then you need a JSON file of the same name as the slot. Its contents
are the command line parameters of aexpect's ``remote_login`` function
of module ``remote``, e.g.::

    {
       "client": "telnet",
       "host": "192.168.64.2",
       "port": "23",
       "username": "root",
       "password": "",
       "prompt": "#"
    }

Final important detail: the remote site also needs avocado
installed.
