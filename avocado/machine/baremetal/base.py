"""
Module that has the base bare metal Machine class definition.

Bare metal machines are more limited in what you can do with them, but
usually you can:

* Control their power status through KVM/Remote Admin systems (such as iLO)
* Check their serial consoles
"""

from avocado.machine.base import Machine


class BareMetalMachine(Machine):

    def __init__(self):
        pass

    def serial_login(self):
        pass
