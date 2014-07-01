"""
Module that has the base Machine class definition.

Machine objects lets you control a machine (poweron/off, boots, reboots).
Every machine has a basic set of attributes, that are augmented as we
move into the specialized classes (that might represent bare metal machines,
virtual machines, so on and so forth).
"""


class Machine(object):

    def __init__(self):
        pass

    def remote_login(self):
        pass

    def serial_login(self):
        pass

    def remote_copy_files(self, src, dst):
        pass
