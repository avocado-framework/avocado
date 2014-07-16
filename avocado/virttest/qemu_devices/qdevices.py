"""
Autotest representation of qemu devices.

These classes implements various features in order to simulate, verify or
interact with qemu qdev structure.

:copyright: 2012-2013 Red Hat Inc.
"""
# Python imports
import logging
import re

# Autotest imports
from utils import DeviceError
from virttest import qemu_monitor
from virttest import utils_misc
import qbuses
import traceback

try:
    # pylint: disable=E0611
    from collections import OrderedDict
except ImportError:
    from virttest.staging.backports.collections import OrderedDict


def _convert_args(arg_dict):
    """
    Convert monitor command arguments dict into humanmonitor string.

    :param arg_dict: The dict of monitor command arguments.
    :return: A string in humanmonitor's 'key=value' format, or a empty
             '' when the dict is empty.
    """
    return ",".join("%s=%s" % (key, val) for key, val in arg_dict.iteritems())


def _build_cmd(cmd, args=None, q_id=None):
    """
    Format QMP command from cmd and args

    :param cmd: Command ('device_add', ...)
    :param q_id: queue id; True = generate random, None = None, str = use str
    """
    obj = {"execute": cmd}
    if args is not None:
        obj["arguments"] = args
    if q_id is True:
        obj["id"] = utils_misc.generate_random_string(8)
    elif q_id is not None:
        obj["id"] = q_id
    return obj


#
# Device objects
#
class QBaseDevice(object):

    """ Base class of qemu objects """

    def __init__(self, dev_type="QBaseDevice", params=None, aobject=None,
                 parent_bus=None, child_bus=None):
        """
        :param dev_type: type of this component
        :param params: component's parameters
        :param aobject: Autotest object which is associated with this device
        :param parent_bus: list of dicts specifying the parent bus
        :param child_bus: list of buses, which this device provides
        """
        self.aid = None         # unique per VM id
        self.type = dev_type    # device type
        self.aobject = aobject  # related autotest object
        if parent_bus is None:
            parent_bus = tuple()
        self.parent_bus = parent_bus   # list of buses into which this dev fits
        self.child_bus = []            # list of buses which this dev provides
        if child_bus is None:
            child_bus = []
        elif not isinstance(child_bus, (list, tuple)):
            self.add_child_bus(child_bus)
        else:
            for bus in child_bus:
                self.add_child_bus(bus)
        self.dynamic_params = []
        self.params = OrderedDict()    # various device params (id, name, ...)
        if params:
            for key, value in params.iteritems():
                self.set_param(key, value)

    def add_child_bus(self, bus):
        """
        Add child bus
        :param bus: Bus, which this device contains
        :type bus: QSparseBus-like
        """
        self.child_bus.append(bus)
        bus.set_device(self)

    def rm_child_bus(self, bus):
        """
        removes child bus
        :param bus: Bus, which this device contains
        :type bus: QSparseBus-like
        """
        self.child_bus.remove(bus)
        bus.set_device(None)

    def set_param(self, option, value, option_type=None, dynamic=False):
        """
        Set device param using qemu notation ("on", "off" instead of bool...)
        :param option: which option's value to set
        :param value: new value
        :param option_type: type of the option (bool)
        :param dynamic: if true value is changed to DYN for not_dynamic compare
        """
        if dynamic:
            if option not in self.dynamic_params:
                self.dynamic_params.append(option)
        else:
            if option in self.dynamic_params:
                self.dynamic_params.remove(option)

        if option_type is bool or isinstance(value, bool):
            if value in ['yes', 'on', True]:
                self.params[option] = "on"
            elif value in ['no', 'off', False]:
                self.params[option] = "off"
        elif value or value == 0:
            if value == "EMPTY_STRING":
                self.params[option] = '""'
            else:
                self.params[option] = value
        elif value is None and option in self.params:
            del(self.params[option])
            if option in self.dynamic_params:
                self.dynamic_params.remove(option)

    def get_param(self, option, default=None):
        """ :return: object param """
        return self.params.get(option, default)

    def __getitem__(self, option):
        """ :return: object param """
        return self.params[option]

    def __delitem__(self, option):
        """ deletes self.params[option] """
        del(self.params[option])

    def __len__(self):
        """ length of self.params """
        return len(self.params)

    def __setitem__(self, option, value):
        """ self.set_param(option, value, None) """
        return self.set_param(option, value)

    def __contains__(self, option):
        """ Is the option set? """
        return option in self.params

    def __str__(self):
        """ :return: Short string representation of this object. """
        return self.str_short()

    def __eq__(self, dev2, dynamic=True):
        """ :return: True when devs are similar, False when different. """
        check_attrs = ['cmdline_nd', 'hotplug_hmp_nd', 'hotplug_qmp_nd']
        try:
            for check_attr in check_attrs:
                try:
                    _ = getattr(self, check_attr)()
                except (DeviceError, NotImplementedError, AttributeError):
                    try:
                        getattr(dev2, check_attr)()
                    except (DeviceError, NotImplementedError, AttributeError):
                        pass
                else:
                    if _ != getattr(dev2, check_attr)():
                        return False
        except Exception:
            logging.error(traceback.format_exc())
            return False
        return True

    def __ne__(self, dev2):
        """ :return: True when devs are different, False when similar. """
        return not self.__eq__(dev2)

    def str_short(self):
        """ Short representation (aid, qid, alternative, type) """
        if self.get_qid():  # Show aid only when it's based on qid
            if self.get_aid():
                return self.get_aid()
            else:
                return "q'%s'" % self.get_qid()
        elif self._get_alternative_name():
            return "a'%s'" % self._get_alternative_name()
        else:
            return "t'%s'" % self.type

    def str_long(self):
        """ Full representation, multi-line with all params """
        out = """%s
  aid = %s
  aobject = %s
  parent_bus = %s
  child_bus = %s
  params:""" % (self.type, self.aid, self.aobject, self.parent_bus,
                self.child_bus)
        for key, value in self.params.iteritems():
            out += "\n    %s = %s" % (key, value)
        return out + '\n'

    def _get_alternative_name(self):
        """ :return: alternative object name """
        return None

    def get_qid(self):
        """ :return: qemu_id """
        return self.params.get('id', '')

    def get_aid(self):
        """ :return: per VM unique autotest_id """
        return self.aid

    def set_aid(self, aid):
        """:param aid: new autotest id for this device"""
        self.aid = aid

    def get_children(self):
        """ :return: List of all children (recursive) """
        children = []
        for bus in self.child_bus:
            children.extend(bus)
        return children

    def cmdline(self):
        """ :return: cmdline command to define this device """
        raise NotImplementedError

    def cmdline_nd(self):
        """
        Command line without dynamic params.

        :return: cmdline command to define this device
                 without dynamic parameters
        """
        self.cmdline()

    # pylint: disable=E0202
    def hotplug(self, monitor):
        """ :return: the output of monitor.cmd() hotplug command """
        if isinstance(monitor, qemu_monitor.QMPMonitor):
            try:
                cmd, args = self.hotplug_qmp()
                return monitor.cmd(cmd, args)
            except DeviceError:     # qmp command not supported
                return monitor.human_monitor_cmd(self.hotplug_hmp())
        elif isinstance(monitor, qemu_monitor.HumanMonitor):
            return monitor.cmd(self.hotplug_hmp())
        else:
            raise TypeError("Invalid monitor object: %s(%s)" % (monitor,
                                                                type(monitor)))

    def hotplug_hmp(self):
        """ :return: the hotplug monitor command """
        raise DeviceError("Hotplug is not supported by this device %s", self)

    def hotplug_qmp(self):
        """ :return: tuple(hotplug qemu command, arguments)"""
        raise DeviceError("Hotplug is not supported by this device %s", self)

    def unplug_hook(self):
        """ Modification prior to unplug can be made here """
        pass

    def unplug_unhook(self):
        """ Roll back the modification made before unplug """
        pass

    def unplug(self, monitor):
        """ :return: the output of monitor.cmd() unplug command """
        if isinstance(monitor, qemu_monitor.QMPMonitor):
            try:
                cmd, args = self.unplug_qmp()
                return monitor.cmd(cmd, args)
            except DeviceError:     # qmp command not supported
                return monitor.human_monitor_cmd(self.unplug_hmp())
        elif isinstance(monitor, qemu_monitor.HumanMonitor):
            return monitor.cmd(self.unplug_hmp())
        else:
            raise TypeError("Invalid monitor object: %s(%s)" % (monitor,
                                                                type(monitor)))

    def unplug_hmp(self):
        """ :return: the unplug monitor command """
        raise DeviceError("Unplug is not supported by this device %s", self)

    def unplug_qmp(self):
        """ :return: tuple(unplug qemu command, arguments)"""
        raise DeviceError("Unplug is not supported by this device %s", self)

    def verify_hotplug(self, out, monitor):
        """
        :param out: Output of the hotplug command
        :param monitor: Monitor used for hotplug
        :return: True when successful, False when unsuccessful, string/None
                 when can't decide.
        """
        return out

    def verify_unplug(self, out, monitor):      # pylint: disable=W0613,R0201
        """
        :param out: Output of the unplug command
        :param monitor: Monitor used for unplug
        """
        return out


class QStringDevice(QBaseDevice):

    """
    General device which allows to specify methods by fixed or parametrizable
    strings in this format:

    ::

        "%(type)s,id=%(id)s,addr=%(addr)s"

    ``params`` will be used to subst ``%()s``
    """

    def __init__(self, dev_type="dummy", params=None, aobject=None,
                 parent_bus=None, child_bus=None, cmdline="", cmdline_nd=None):
        """
        :param dev_type: type of this component
        :param params: component's parameters
        :param aobject: Autotest object which is associated with this device
        :param parent_bus: bus(es), in which this device is plugged in
        :param child_bus: bus, which this device provides
        :param cmdline: cmdline string
        """
        super(QStringDevice, self).__init__(dev_type, params, aobject,
                                            parent_bus, child_bus)
        self._cmdline = cmdline
        self._cmdline_nd = cmdline_nd
        if cmdline_nd is None:
            self._cmdline_nd = cmdline

    def cmdline(self):
        """ :return: cmdline command to define this device """
        try:
            if self._cmdline:
                return self._cmdline % self.params
        except KeyError, details:
            raise KeyError("Param %s required for cmdline is not present in %s"
                           % (details, self.str_long()))

    def cmdline_nd(self):
        """
        Command line without dynamic parameters.

        :return: cmdline command to define this device without dynamic parameters.
        """
        try:
            if self._cmdline_nd:
                return self._cmdline_nd % self.params
        except KeyError, details:
            raise KeyError("Param %s required for cmdline is not present in %s"
                           % (details, self.str_long()))


class QCustomDevice(QBaseDevice):

    """
    Representation of the '-$option $param1=$value1,$param2...' qemu object.
    This representation handles only cmdline.
    """

    def __init__(self, dev_type, params=None, aobject=None,
                 parent_bus=None, child_bus=None, backend=None):
        """
        :param dev_type: The desired -$option parameter (device, chardev, ..)
        """
        super(QCustomDevice, self).__init__(dev_type, params, aobject,
                                            parent_bus, child_bus)
        if backend:
            self.__backend = backend
        else:
            self.__backend = None

    def cmdline(self):
        """ :return: cmdline command to define this device """
        if self.__backend and self.params.get(self.__backend):
            out = "-%s %s," % (self.type, self.params.get(self.__backend))
            params = self.params.copy()
            del params[self.__backend]
        else:
            out = "-%s " % self.type
            params = self.params
        for key, value in params.iteritems():
            if value != "NO_EQUAL_STRING":
                out += "%s=%s," % (key, value)
            else:
                out += "%s," % key
        if out[-1] == ',':
            out = out[:-1]
        return out

    def cmdline_nd(self):
        """
        Command line without dynamic parameters.

        :return: cmdline command to define this device without dynamic parameters.
        """
        if self.__backend and self.params.get(self.__backend):
            out = "-%s %s," % (self.type, self.params.get(self.__backend))
            params = self.params.copy()
            del params[self.__backend]
        else:
            out = "-%s " % self.type
            params = self.params
        for key, value in params.iteritems():
            if value != "NO_EQUAL_STRING":
                if key in self.dynamic_params:
                    out += "%s=DYN," % (key,)
                else:
                    out += "%s=%s," % (key, value)
            else:
                out += "%s," % key
        if out[-1] == ',':
            out = out[:-1]
        return out


class QDrive(QCustomDevice):

    """
    Representation of the '-drive' qemu object without hotplug support.
    """

    def __init__(self, aobject, use_device=True):
        child_bus = qbuses.QDriveBus('drive_%s' % aobject, aobject)
        super(QDrive, self).__init__("drive", {}, aobject, (),
                                     child_bus)
        if use_device:
            self.params['id'] = 'drive_%s' % aobject

    def set_param(self, option, value, option_type=None):
        """
        Set device param using qemu notation ("on", "off" instead of bool...)
        It restricts setting of the 'id' param as it's automatically created.
        :param option: which option's value to set
        :param value: new value
        :param option_type: type of the option (bool)
        """
        if option == 'id':
            raise KeyError("Drive ID is automatically created from aobject. %s"
                           % self)
        elif option == 'bus':
            # Workaround inconsistency between -drive and -device
            value = re.findall(r'(\d+)', value)
            if value is not None:
                value = value[0]
        super(QDrive, self).set_param(option, value, option_type)


class QOldDrive(QDrive):

    """
    This is a variant for -drive without 'addr' support
    """

    def set_param(self, option, value, option_type=None):
        """
        Ignore addr parameters as they are not supported by old qemus
        """
        if option == 'addr':
            logging.warn("Ignoring 'addr=%s' parameter of %s due of old qemu"
                         ", PCI addresses might be messed up.", value,
                         self.str_short())
            return
        return super(QOldDrive, self).set_param(option, value, option_type)


class QHPDrive(QDrive):

    """
    Representation of the '-drive' qemu object with hotplug support.
    """

    def __init__(self, aobject):
        super(QHPDrive, self).__init__(aobject)
        self.__hook_drive_bus = None

    def verify_hotplug(self, out, monitor):
        if isinstance(monitor, qemu_monitor.QMPMonitor):
            if out.startswith('OK'):
                return True
        else:
            if out == 'OK':
                return True
        return False

    def verify_unplug(self, out, monitor):
        out = monitor.info("qtree", debug=False)
        if "unknown command" in out:       # Old qemu don't have info qtree
            return True
        dev_id_name = 'id "%s"' % self.aid
        if dev_id_name in out:
            return False
        else:
            return True

    def get_children(self):
        """ Device bus should be removed too """
        for bus in self.child_bus:
            if isinstance(bus, qbuses.QDriveBus):
                drive_bus = bus
                self.rm_child_bus(bus)
                break
        devices = super(QHPDrive, self).get_children()
        self.add_child_bus(drive_bus)
        return devices

    def unplug_hook(self):
        """
        Devices from this bus are not removed, only 'drive' is set to None.
        """
        for bus in self.child_bus:
            if isinstance(bus, qbuses.QDriveBus):
                for dev in bus:
                    self.__hook_drive_bus = dev.get_param('drive')
                    dev['drive'] = None
                break

    def unplug_unhook(self):
        """ Set back the previous 'drive' (unsafe, using the last value) """
        if self.__hook_drive_bus is not None:
            for bus in self.child_bus:
                if isinstance(bus, qbuses.QDriveBus):
                    for dev in bus:
                        dev['drive'] = self.__hook_drive_bus
                    break

    def hotplug_hmp(self):
        """ :return: the hotplug monitor command """
        args = self.params.copy()
        pci_addr = args.pop('addr', 'auto')
        args = _convert_args(args)
        return "drive_add %s %s" % (pci_addr, args)

    def unplug_hmp(self):
        """ :return: the unplug monitor command """
        if self.get_qid() is None:
            raise DeviceError("qid not set; device %s can't be unplugged"
                              % self)
        return "drive_del %s" % self.get_qid()


class QRHDrive(QDrive):

    """
    Representation of the '-drive' qemu object with RedHat hotplug support.
    """

    def __init__(self, aobject):
        super(QRHDrive, self).__init__(aobject)
        self.__hook_drive_bus = None

    def hotplug_hmp(self):
        """ :return: the hotplug monitor command """
        args = self.params.copy()
        args.pop('addr', None)    # not supported by RHDrive
        args.pop('if', None)
        args = _convert_args(args)
        return "__com.redhat_drive_add %s" % args

    def hotplug_qmp(self):
        """ :return: the hotplug monitor command """
        args = self.params.copy()
        args.pop('addr', None)    # not supported by RHDrive
        args.pop('if', None)
        return "__com.redhat_drive_add", args

    def get_children(self):
        """ Device bus should be removed too """
        for bus in self.child_bus:
            if isinstance(bus, qbuses.QDriveBus):
                drive_bus = bus
                self.rm_child_bus(bus)
                break
        devices = super(QRHDrive, self).get_children()
        self.add_child_bus(drive_bus)
        return devices

    def unplug_hook(self):
        """
        Devices from this bus are not removed, only 'drive' is set to None.
        """
        for bus in self.child_bus:
            if isinstance(bus, qbuses.QDriveBus):
                for dev in bus:
                    self.__hook_drive_bus = dev.get_param('drive')
                    dev['drive'] = None
                break

    def unplug_unhook(self):
        """ Set back the previous 'drive' (unsafe, using the last value) """
        if self.__hook_drive_bus is not None:
            for bus in self.child_bus:
                if isinstance(bus, qbuses.QDriveBus):
                    for dev in bus:
                        dev['drive'] = self.__hook_drive_bus
                    break

    def unplug_hmp(self):
        """ :return: the unplug monitor command """
        if self.get_qid() is None:
            raise DeviceError("qid not set; device %s can't be unplugged"
                              % self)
        return "__com.redhat_drive_del %s" % self.get_qid()

    def unplug_qmp(self):
        """ :return: the unplug monitor command """
        if self.get_qid() is None:
            raise DeviceError("qid not set; device %s can't be unplugged"
                              % self)
        return "__com.redhat_drive_del", {'id': self.get_qid()}


class QDevice(QCustomDevice):

    """
    Representation of the '-device' qemu object. It supports all methods.
    :note: Use driver format in full form - 'driver' = '...' (usb-ehci, ide-hd)
    """

    def __init__(self, driver=None, params=None, aobject=None,
                 parent_bus=None, child_bus=None):
        super(QDevice, self).__init__("device", params, aobject, parent_bus,
                                      child_bus, 'driver')
        if driver:
            self.set_param('driver', driver)
        self.hook_drive_bus = None

    def _get_alternative_name(self):
        """ :return: alternative object name """
        if self.params.get('driver'):
            return self.params.get('driver')

    def hotplug_hmp(self):
        """ :return: the hotplug monitor command """
        if self.params.get('driver'):
            params = self.params.copy()
            out = "device_add %s" % params.pop('driver')
            params = _convert_args(params)
            if params:
                out += ",%s" % params
        else:
            out = "device_add %s" % _convert_args(self.params)
        return out

    def hotplug_qmp(self):
        """ :return: the hotplug monitor command """
        return "device_add", self.params

    def hotplug_hmp_nd(self):
        """ :return: the hotplug monitor command without dynamic parameters"""
        if self.params.get('driver'):
            params = self.params.copy()
            out = "device_add %s" % params.pop('driver')
            for key in self.dynamic_params:
                params[key] = "DYN"
            params = _convert_args(params)
            if params:
                out += ",%s" % params
        else:
            params = self.params.copy()
            for key in self.dynamic_params:
                params[key] = "DYN"
            out = "device_add %s" % _convert_args(params)
        return out

    def hotplug_qmp_nd(self):
        """ :return: the hotplug monitor command without dynamic parameters"""
        params = self.params.copy()
        for key in self.dynamic_params:
            params[key] = "DYN"
        return "device_add", params

    def get_children(self):
        """ Device bus should be removed too """
        devices = super(QDevice, self).get_children()
        if self.hook_drive_bus:
            devices.append(self.hook_drive_bus)
        return devices

    def unplug_hmp(self):
        """ :return: the unplug monitor command """
        if self.get_qid():
            return "device_del %s" % self.get_qid()
        else:
            raise DeviceError("Device has no qemu_id.")

    def unplug_qmp(self):
        """ :return: the unplug monitor command """
        if self.get_qid():
            return "device_del", {'id': self.get_qid()}
        else:
            raise DeviceError("Device has no qemu_id.")

    def verify_unplug(self, out, monitor):
        out = monitor.info("qtree", debug=False)
        if "unknown command" in out:       # Old qemu don't have info qtree
            return out
        dev_id_name = 'id "%s"' % self.get_qid()
        if dev_id_name in out:
            return False
        else:
            return True

    # pylint: disable=E0202
    def verify_hotplug(self, out, monitor):
        out = monitor.info("qtree", debug=False)
        if "unknown command" in out:       # Old qemu don't have info qtree
            return out
        dev_id_name = 'id "%s"' % self.get_qid()
        if dev_id_name in out:
            return True
        else:
            return False


class QGlobal(QBaseDevice):

    """
    Representation of qemu global setting (-global driver.property=value)
    """

    def __init__(self, driver, prop, value, aobject=None,
                 parent_bus=None, child_bus=None):
        """
        :param driver: Which global driver to set
        :param prop: Which property to set
        :param value: What's the desired value
        :param params: component's parameters
        :param aobject: Autotest object which is associated with this device
        :param parent_bus: bus(es), in which this device is plugged in
        :param child_bus: bus, which this device provides
        """
        params = {'driver': driver, 'property': prop, 'value': value}
        super(QGlobal, self).__init__('global', params, aobject,
                                      parent_bus, child_bus)

    def cmdline(self):
        return "-global %s.%s=%s" % (self['driver'], self['property'],
                                     self['value'])


class QFloppy(QGlobal):

    """
    Imitation of qemu floppy disk defined by -global isa-fdc.drive?=$drive
    """

    def __init__(self, unit=None, drive=None, aobject=None, parent_bus=None,
                 child_bus=None):
        """
        :param unit: Floppy unit (None, 0, 1 or driveA, driveB)
        :param drive: id of drive
        :param aobject: Autotest object which is associated with this device
        :param parent_bus: bus(es), in which this device is plugged in
        :param child_bus: bus(es), which this device provides
        """
        super(QFloppy, self).__init__('isa-fdc', unit, drive, aobject,
                                      parent_bus, child_bus)

    def _get_alternative_name(self):
        return "floppy-%s" % (self.get_param('property'))

    def set_param(self, option, value, option_type=None):
        """
        drive and unit params have to be 'translated' as value and property.
        """
        if option == 'drive':
            option = 'value'
        elif option == 'unit':
            option = 'property'
        super(QFloppy, self).set_param(option, value, option_type)
