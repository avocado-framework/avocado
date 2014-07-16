"""
Module that has the base virtual Machine class definition.

Virtual machines have common features that bare metal machines don't, such
as the ability to be paused or migrated (have their internal state transfered
to another instance, in the same host or on a different host).

More specialized virtual machines have more features, and it is up to the
tester to use those extra features.
"""

from avocado.machine.base import Machine


class VirtualMachine(Machine):

    def __init__(self):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def is_alive(self):
        pass

    def is_dead(self):
        pass

    def migrate(self):
        pass

    def screenshot(self):
        pass
