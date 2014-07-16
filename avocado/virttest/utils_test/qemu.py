"""
High-level QEMU test utility functions.

This module is meant to reduce code size by performing common test procedures.
Generally, code here should look like test code.

More specifically:
    - Functions in this module should raise exceptions if things go wrong
    - Functions in this module typically use functions and classes from
      lower-level modules (e.g. utils_misc, qemu_vm, aexpect).
    - Functions in this module should not be used by lower-level modules.
    - Functions in this module should be used in the right context.
      For example, a function should not be used where it may display
      misleading or inaccurate info or debug messages.

:copyright: 2008-2013 Red Hat Inc.
"""

import commands
import cPickle
import errno
import fcntl
import logging
import os
import re
import socket
import threading
import time

from autotest.client import utils
from autotest.client.shared import error
from autotest.client.shared.syncdata import SyncData, SyncListenServer

from virttest import env_process, remote, storage, utils_misc

try:
    from virttest.staging import utils_memory
except ImportError:
    from autotest.client.shared import utils_memory


def guest_active(vm):
    o = vm.monitor.info("status")
    if isinstance(o, str):
        return "status: running" in o
    else:
        if "status" in o:
            return o.get("status") == "running"
        else:
            return o.get("running")


def get_numa_status(numa_node_info, qemu_pid, debug=True):
    """
    Get the qemu process memory use status and the cpu list in each node.

    :param numa_node_info: Host numa node information
    :type numa_node_info: NumaInfo object
    :param qemu_pid: process id of qemu
    :type numa_node_info: string
    :param debug: Print the debug info or not
    :type debug: bool
    :return: memory and cpu list in each node
    :rtype: tuple
    """
    node_list = numa_node_info.online_nodes
    qemu_memory = []
    qemu_cpu = []
    cpus = utils_misc.get_pid_cpu(qemu_pid)
    for node_id in node_list:
        qemu_memory_status = utils_memory.read_from_numa_maps(qemu_pid,
                                                              "N%d" % node_id)
        memory = sum([int(_) for _ in qemu_memory_status.values()])
        qemu_memory.append(memory)
        cpu = [_ for _ in cpus if _ in numa_node_info.nodes[node_id].cpus]
        qemu_cpu.append(cpu)
        if debug:
            logging.debug("qemu-kvm process using %s pages and cpu %s in "
                          "node %s" % (memory, " ".join(cpu), node_id))
    return (qemu_memory, qemu_cpu)


def pin_vm_threads(vm, node):
    """
    Pin VM threads to single cpu of a numa node

    :param vm: VM object
    :param node: NumaNode object
    """
    if len(vm.vcpu_threads) + len(vm.vhost_threads) < len(node.cpus):
        for i in vm.vcpu_threads:
            logging.info("pin vcpu thread(%s) to cpu(%s)" % (i, node.pin_cpu(i)))
        for i in vm.vhost_threads:
            logging.info("pin vhost thread(%s) to cpu(%s)" % (i, node.pin_cpu(i)))
    elif (len(vm.vcpu_threads) <= len(node.cpus) and
          len(vm.vhost_threads) <= len(node.cpus)):
        for i in vm.vcpu_threads:
            logging.info("pin vcpu thread(%s) to cpu(%s)" %
                         (i, node.pin_cpu(i)))
        for i in vm.vhost_threads:
            logging.info("pin vhost thread(%s) to extra cpu(%s)" %
                         (i, node.pin_cpu(i, extra=True)))
    else:
        logging.info("Skip pinning, no enough nodes")


def migrate(vm, env=None, mig_timeout=3600, mig_protocol="tcp",
            mig_cancel=False, offline=False, stable_check=False,
            clean=False, save_path=None, dest_host='localhost', mig_port=None):
    """
    Migrate a VM locally and re-register it in the environment.

    :param vm: The VM to migrate.
    :param env: The environment dictionary.  If omitted, the migrated VM will
            not be registered.
    :param mig_timeout: timeout value for migration.
    :param mig_protocol: migration protocol
    :param mig_cancel: Test migrate_cancel or not when protocol is tcp.
    :param dest_host: Destination host (defaults to 'localhost').
    :param mig_port: Port that will be used for migration.
    :return: The post-migration VM, in case of same host migration, True in
            case of multi-host migration.
    """
    def mig_finished():
        try:
            o = vm.monitor.info("migrate")
            if isinstance(o, str):
                return "status: active" not in o
            else:
                return o.get("status") != "active"
        except Exception:
            pass

    def mig_succeeded():
        o = vm.monitor.info("migrate")
        if isinstance(o, str):
            return "status: completed" in o
        else:
            return o.get("status") == "completed"

    def mig_failed():
        o = vm.monitor.info("migrate")
        if isinstance(o, str):
            return "status: failed" in o
        else:
            return o.get("status") == "failed"

    def mig_cancelled():
        o = vm.monitor.info("migrate")
        if isinstance(o, str):
            return ("Migration status: cancelled" in o or
                    "Migration status: canceled" in o)
        else:
            return (o.get("status") == "cancelled" or
                    o.get("status") == "canceled")

    def wait_for_migration():
        if not utils_misc.wait_for(mig_finished, mig_timeout, 2, 2,
                                   "Waiting for migration to finish"):
            raise error.TestFail("Timeout expired while waiting for migration "
                                 "to finish")

    if dest_host == 'localhost':
        dest_vm = vm.clone()

    if (dest_host == 'localhost') and stable_check:
        # Pause the dest vm after creation
        dest_vm.params['extra_params'] = (dest_vm.params.get('extra_params', '')
                                          + ' -S')

    if dest_host == 'localhost':
        dest_vm.create(migration_mode=mig_protocol, mac_source=vm)

    try:
        try:
            if mig_protocol in ["tcp", "rdma", "x-rdma"]:
                if dest_host == 'localhost':
                    uri = mig_protocol + ":0:%d" % dest_vm.migration_port
                else:
                    uri = mig_protocol + ':%s:%d' % (dest_host, mig_port)
            elif mig_protocol == "unix":
                uri = "unix:%s" % dest_vm.migration_file
            elif mig_protocol == "exec":
                uri = '"exec:nc localhost %s"' % dest_vm.migration_port

            if offline:
                vm.pause()
            vm.monitor.migrate(uri)

            if mig_cancel:
                time.sleep(2)
                vm.monitor.cmd("migrate_cancel")
                if not utils_misc.wait_for(mig_cancelled, 60, 2, 2,
                                           "Waiting for migration "
                                           "cancellation"):
                    raise error.TestFail("Failed to cancel migration")
                if offline:
                    vm.resume()
                if dest_host == 'localhost':
                    dest_vm.destroy(gracefully=False)
                return vm
            else:
                wait_for_migration()
                if (dest_host == 'localhost') and stable_check:
                    save_path = None or "/tmp"
                    save1 = os.path.join(save_path, "src")
                    save2 = os.path.join(save_path, "dst")

                    vm.save_to_file(save1)
                    dest_vm.save_to_file(save2)

                    # Fail if we see deltas
                    md5_save1 = utils.hash_file(save1)
                    md5_save2 = utils.hash_file(save2)
                    if md5_save1 != md5_save2:
                        raise error.TestFail("Mismatch of VM state before "
                                             "and after migration")

                if (dest_host == 'localhost') and offline:
                    dest_vm.resume()
        except Exception:
            if dest_host == 'localhost':
                dest_vm.destroy()
            raise

    finally:
        if (dest_host == 'localhost') and stable_check and clean:
            logging.debug("Cleaning the state files")
            if os.path.isfile(save1):
                os.remove(save1)
            if os.path.isfile(save2):
                os.remove(save2)

    # Report migration status
    if mig_succeeded():
        logging.info("Migration finished successfully")
    elif mig_failed():
        raise error.TestFail("Migration failed")
    else:
        status = vm.monitor.info("migrate")
        raise error.TestFail("Migration ended with unknown status: %s" %
                             status)

    if dest_host == 'localhost':
        if dest_vm.monitor.verify_status("paused"):
            logging.debug("Destination VM is paused, resuming it")
            dest_vm.resume()

    # Kill the source VM
    vm.destroy(gracefully=False)

    # Replace the source VM with the new cloned VM
    if (dest_host == 'localhost') and (env is not None):
        env.register_vm(vm.name, dest_vm)

    # Return the new cloned VM
    if dest_host == 'localhost':
        return dest_vm
    else:
        return vm


class MigrationData(object):

    def __init__(self, params, srchost, dsthost, vms_name, params_append):
        """
        Class that contains data needed for one migration.
        """
        self.params = params.copy()
        self.params.update(params_append)

        self.source = False
        if params.get("hostid") == srchost:
            self.source = True

        self.destination = False
        if params.get("hostid") == dsthost:
            self.destination = True

        self.src = srchost
        self.dst = dsthost
        self.hosts = [srchost, dsthost]
        self.mig_id = {'src': srchost, 'dst': dsthost, "vms": vms_name}
        self.vms_name = vms_name
        self.vms = []
        self.vm_ports = None

    def is_src(self):
        """
        :return: True if host is source.
        """
        return self.source

    def is_dst(self):
        """
        :return: True if host is destination.
        """
        return self.destination


class MultihostMigration(object):

    """
    Class that provides a framework for multi-host migration.

    Migration can be run both synchronously and asynchronously.
    To specify what is going to happen during the multi-host
    migration, it is necessary to reimplement the method
    migration_scenario. It is possible to start multiple migrations
    in separate threads, since self.migrate is thread safe.

    Only one test using multihost migration framework should be
    started on one machine otherwise it is necessary to solve the
    problem with listen server port.

    Multihost migration starts SyncListenServer through which
    all messages are transferred, since the multiple hosts can
    be in different states.

    Class SyncData is used to transfer data over network or
    synchronize the migration process. Synchronization sessions
    are recognized by session_id.

    It is important to note that, in order to have multi-host
    migration, one needs shared guest image storage. The simplest
    case is when the guest images are on an NFS server.

    Example:

    ::

        class TestMultihostMigration(utils_misc.MultihostMigration):
            def __init__(self, test, params, env):
                super(testMultihostMigration, self).__init__(test, params, env)

            def migration_scenario(self):
                srchost = self.params.get("hosts")[0]
                dsthost = self.params.get("hosts")[1]

                def worker(mig_data):
                    vm = env.get_vm("vm1")
                    session = vm.wait_for_login(timeout=self.login_timeout)
                    session.sendline("nohup dd if=/dev/zero of=/dev/null &")
                    session.cmd("killall -0 dd")

                def check_worker(mig_data):
                    vm = env.get_vm("vm1")
                    session = vm.wait_for_login(timeout=self.login_timeout)
                    session.cmd("killall -9 dd")

                # Almost synchronized migration, waiting to end it.
                # Work is started only on first VM.
                self.migrate_wait(["vm1", "vm2"], srchost, dsthost,
                                  worker, check_worker)

                # Migration started in different threads.
                # It allows to start multiple migrations simultaneously.
                mig1 = self.migrate(["vm1"], srchost, dsthost,
                                    worker, check_worker)
                mig2 = self.migrate(["vm2"], srchost, dsthost)
                mig2.join()
                mig1.join()

        mig = TestMultihostMigration(test, params, env)
        mig.run()
    """

    def __init__(self, test, params, env, preprocess_env=True):
        self.test = test
        self.params = params
        self.env = env
        self.hosts = params.get("hosts")
        self.hostid = params.get('hostid', "")
        self.comm_port = int(params.get("comm_port", 13234))
        vms_count = len(params["vms"].split())

        self.login_timeout = int(params.get("login_timeout", 360))
        self.disk_prepare_timeout = int(params.get("disk_prepare_timeout",
                                                   160 * vms_count))
        self.finish_timeout = int(params.get("finish_timeout",
                                             120 * vms_count))

        self.new_params = None

        if params.get("clone_master") == "yes":
            self.clone_master = True
        else:
            self.clone_master = False

        self.mig_timeout = int(params.get("mig_timeout"))
        # Port used to communicate info between source and destination
        self.regain_ip_cmd = params.get("regain_ip_cmd", None)
        self.not_login_after_mig = params.get("not_login_after_mig", None)

        self.vm_lock = threading.Lock()

        self.sync_server = None
        if self.clone_master:
            self.sync_server = SyncListenServer()

        if preprocess_env:
            self.preprocess_env()
            self._hosts_barrier(self.hosts, self.hosts, 'disk_prepared',
                                self.disk_prepare_timeout)

    def migration_scenario(self):
        """
        Multi Host migration_scenario is started from method run where the
        exceptions are checked. It is not necessary to take care of
        cleaning up after test crash or finish.
        """
        raise NotImplementedError

    def post_migration(self, vm, cancel_delay, mig_offline, dsthost, vm_ports,
                       not_wait_for_migration, fd, mig_data):
        pass

    def migrate_vms_src(self, mig_data):
        """
        Migrate vms source.

        :param mig_Data: Data for migration.

        For change way how machine migrates is necessary
        re implement this method.
        """
        def mig_wrapper(vm, cancel_delay, dsthost, vm_ports,
                        not_wait_for_migration, mig_offline, mig_data):
            vm.migrate(cancel_delay=cancel_delay, offline=mig_offline,
                       dest_host=dsthost, remote_port=vm_ports[vm.name],
                       not_wait_for_migration=not_wait_for_migration)

            self.post_migration(vm, cancel_delay, mig_offline, dsthost,
                                vm_ports, not_wait_for_migration, None,
                                mig_data)

        logging.info("Start migrating now...")
        cancel_delay = mig_data.params.get("cancel_delay")
        if cancel_delay is not None:
            cancel_delay = int(cancel_delay)
        not_wait_for_migration = mig_data.params.get("not_wait_for_migration")
        if not_wait_for_migration == "yes":
            not_wait_for_migration = True
        mig_offline = mig_data.params.get("mig_offline")
        if mig_offline == "yes":
            mig_offline = True
        else:
            mig_offline = False

        multi_mig = []
        for vm in mig_data.vms:
            multi_mig.append((mig_wrapper, (vm, cancel_delay, mig_data.dst,
                                            mig_data.vm_ports,
                                            not_wait_for_migration,
                                            mig_offline, mig_data)))
        utils_misc.parallel(multi_mig)

    def migrate_vms_dest(self, mig_data):
        """
        Migrate vms destination. This function is started on dest host during
        migration.

        :param mig_Data: Data for migration.
        """
        pass

    def __del__(self):
        if self.sync_server:
            self.sync_server.close()

    def master_id(self):
        return self.hosts[0]

    def _hosts_barrier(self, hosts, session_id, tag, timeout):
        logging.debug("Barrier timeout: %d tags: %s" % (timeout, tag))
        tags = SyncData(self.master_id(), self.hostid, hosts,
                        "%s,%s,barrier" % (str(session_id), tag),
                        self.sync_server).sync(tag, timeout)
        logging.debug("Barrier tag %s" % (tags))

    def preprocess_env(self):
        """
        Prepare env to start vms.
        """
        storage.preprocess_images(self.test.bindir, self.params, self.env)

    def _check_vms_source(self, mig_data):
        start_mig_tout = mig_data.params.get("start_migration_timeout", None)
        if start_mig_tout is None:
            for vm in mig_data.vms:
                vm.wait_for_login(timeout=self.login_timeout)

        if mig_data.params.get("host_mig_offline") != "yes":
            sync = SyncData(self.master_id(), self.hostid, mig_data.hosts,
                            mig_data.mig_id, self.sync_server)
            mig_data.vm_ports = sync.sync(timeout=240)[mig_data.dst]
            logging.info("Received from destination the migration port %s",
                         str(mig_data.vm_ports))

    def _check_vms_dest(self, mig_data):
        mig_data.vm_ports = {}
        for vm in mig_data.vms:
            logging.info("Communicating to source migration port %s",
                         vm.migration_port)
            mig_data.vm_ports[vm.name] = vm.migration_port

        if mig_data.params.get("host_mig_offline") != "yes":
            SyncData(self.master_id(), self.hostid,
                     mig_data.hosts, mig_data.mig_id,
                     self.sync_server).sync(mig_data.vm_ports, timeout=240)

    def _prepare_params(self, mig_data):
        """
        Prepare separate params for vm migration.

        :param vms_name: List of vms.
        """
        new_params = mig_data.params.copy()
        new_params["vms"] = " ".join(mig_data.vms_name)
        return new_params

    def _check_vms(self, mig_data):
        """
        Check if vms are started correctly.

        :param vms: list of vms.
        :param source: Must be True if is source machine.
        """
        if mig_data.is_src():
            self._check_vms_source(mig_data)
        else:
            self._check_vms_dest(mig_data)

    def _quick_check_vms(self, mig_data):
        """
        Check if vms are started correctly.

        :param vms: list of vms.
        :param source: Must be True if is source machine.
        """
        logging.info("Try check vms %s" % (mig_data.vms_name))
        for vm in mig_data.vms_name:
            if self.env.get_vm(vm) not in mig_data.vms:
                mig_data.vms.append(self.env.get_vm(vm))
        for vm in mig_data.vms:
            logging.info("Check vm %s on host %s" % (vm.name, self.hostid))
            vm.verify_alive()

    def prepare_for_migration(self, mig_data, migration_mode):
        """
        Prepare destination of migration for migration.

        :param mig_data: Class with data necessary for migration.
        :param migration_mode: Migration mode for prepare machine.
        """
        new_params = self._prepare_params(mig_data)

        new_params['migration_mode'] = migration_mode
        new_params['start_vm'] = 'yes'

        if self.params.get("migration_sync_vms", "no") == "yes":
            if mig_data.is_src():
                self.vm_lock.acquire()
                env_process.process(self.test, new_params, self.env,
                                    env_process.preprocess_image,
                                    env_process.preprocess_vm)
                self.vm_lock.release()
                self._quick_check_vms(mig_data)

                # Send vms configuration to dst host.
                vms = cPickle.dumps([self.env.get_vm(vm_name)
                                     for vm_name in mig_data.vms_name])

                self.env.get_vm(mig_data.vms_name[0]).monitor.info("qtree")
                SyncData(self.master_id(), self.hostid,
                         mig_data.hosts, mig_data.mig_id,
                         self.sync_server).sync(vms, timeout=240)
            elif mig_data.is_dst():
                # Load vms configuration from src host.
                vms = cPickle.loads(SyncData(self.master_id(), self.hostid,
                                             mig_data.hosts, mig_data.mig_id,
                                             self.sync_server).sync(timeout=240)[mig_data.src])
                for vm in vms:
                    # Save config to env. Used for create machine.
                    # When reuse_previous_config params is set don't check
                    # machine.
                    vm.address_cache = self.env.get("address_cache")
                    self.env.register_vm(vm.name, vm)

                self.vm_lock.acquire()
                env_process.process(self.test, new_params, self.env,
                                    env_process.preprocess_image,
                                    env_process.preprocess_vm)
                vms[0].monitor.info("qtree")
                self.vm_lock.release()
                self._quick_check_vms(mig_data)
        else:
            self.vm_lock.acquire()
            env_process.process(self.test, new_params, self.env,
                                env_process.preprocess_image,
                                env_process.preprocess_vm)
            self.vm_lock.release()
            self._quick_check_vms(mig_data)

        self._check_vms(mig_data)

    def migrate_vms(self, mig_data):
        """
        Migrate vms.
        """
        if mig_data.is_src():
            self.migrate_vms_src(mig_data)
        else:
            self.migrate_vms_dest(mig_data)

    def check_vms_dst(self, mig_data):
        """
        Check vms after migrate.

        :param mig_data: object with migration data.
        """
        for vm in mig_data.vms:
            vm.resume()
            if not guest_active(vm):
                raise error.TestFail("Guest not active after migration")

        logging.info("Migrated guest appears to be running")

        logging.info("Logging into migrated guest after migration...")
        for vm in mig_data.vms:
            if self.regain_ip_cmd is not None:
                session_serial = vm.wait_for_serial_login(timeout=self.login_timeout)
                # There is sometime happen that system sends some message on
                # serial console and IP renew command block test. Because
                # there must be added "sleep" in IP renew command.
                session_serial.cmd(self.regain_ip_cmd)

            if not self.not_login_after_mig:
                vm.wait_for_login(timeout=self.login_timeout)

    def check_vms_src(self, mig_data):
        """
        Check vms after migrate.

        :param mig_data: object with migration data.
        """
        pass

    def postprocess_env(self):
        """
        Kill vms and delete cloned images.
        """
        pass

    def before_migration(self, mig_data):
        """
        Do something right before migration.

        :param mig_data: object with migration data.
        """
        pass

    def migrate(self, vms_name, srchost, dsthost, start_work=None,
                check_work=None, mig_mode="tcp", params_append=None):
        """
        Migrate machine from srchost to dsthost. It executes start_work on
        source machine before migration and executes check_work on dsthost
        after migration.

        Migration execution progress:

        ::

            source host                   |   dest host
            --------------------------------------------------------
               prepare guest on both sides of migration
                - start machine and check if machine works
                - synchronize transfer data needed for migration
            --------------------------------------------------------
            start work on source guests   |   wait for migration
            --------------------------------------------------------
                         migrate guest to dest host.
                  wait on finish migration synchronization
            --------------------------------------------------------
                                          |   check work on vms
            --------------------------------------------------------
                        wait for sync on finish migration

        :param vms_name: List of vms.
        :param srchost: src host id.
        :param dsthost: dst host id.
        :param start_work: Function started before migration.
        :param check_work: Function started after migration.
        :param mig_mode: Migration mode.
        :param params_append: Append params to self.params only for migration.
        """
        def migrate_wrap(vms_name, srchost, dsthost, start_work=None,
                         check_work=None, params_append=None):
            logging.info("Starting migrate vms %s from host %s to %s" %
                         (vms_name, srchost, dsthost))
            pause = self.params.get("paused_after_start_vm")
            mig_error = None
            mig_data = MigrationData(self.params, srchost, dsthost,
                                     vms_name, params_append)
            cancel_delay = self.params.get("cancel_delay", None)
            host_offline_migration = self.params.get("host_mig_offline")

            try:
                try:
                    if mig_data.is_src():
                        self.prepare_for_migration(mig_data, None)
                    elif self.hostid == dsthost:
                        if host_offline_migration != "yes":
                            self.prepare_for_migration(mig_data, mig_mode)
                    else:
                        return

                    if mig_data.is_src():
                        if start_work:
                            if pause != "yes":
                                start_work(mig_data)
                            else:
                                raise error.TestNAError("Can't start work if "
                                                        "vm is paused.")

                    # Starts VM and waits timeout before migration.
                    if pause == "yes" and mig_data.is_src():
                        for vm in mig_data.vms:
                            vm.resume()
                        wait = self.params.get("start_migration_timeout", 0)
                        logging.debug("Wait for migraiton %s seconds." %
                                      (wait))
                        time.sleep(int(wait))

                    self.before_migration(mig_data)

                    self.migrate_vms(mig_data)

                    timeout = 60
                    if cancel_delay is None:
                        if host_offline_migration == "yes":
                            self._hosts_barrier(self.hosts,
                                                mig_data.mig_id,
                                                'wait_for_offline_mig',
                                                self.finish_timeout)
                            if mig_data.is_dst():
                                self.prepare_for_migration(mig_data, mig_mode)
                            self._hosts_barrier(self.hosts,
                                                mig_data.mig_id,
                                                'wait2_for_offline_mig',
                                                self.finish_timeout)

                        if (not mig_data.is_src()):
                            timeout = self.mig_timeout
                        self._hosts_barrier(mig_data.hosts, mig_data.mig_id,
                                            'mig_finished', timeout)

                        if mig_data.is_dst():
                            self.check_vms_dst(mig_data)
                            if check_work:
                                check_work(mig_data)
                        else:
                            self.check_vms_src(mig_data)
                            if check_work:
                                check_work(mig_data)
                except:
                    mig_error = True
                    raise
            finally:
                if mig_error and cancel_delay is not None:
                    self._hosts_barrier(self.hosts,
                                        mig_data.mig_id,
                                        'test_finihed',
                                        self.finish_timeout)
                elif mig_error:
                    raise

        def wait_wrap(vms_name, srchost, dsthost):
            mig_data = MigrationData(self.params, srchost, dsthost, vms_name,
                                     None)
            timeout = (self.login_timeout + self.mig_timeout +
                       self.finish_timeout)

            self._hosts_barrier(self.hosts, mig_data.mig_id,
                                'test_finihed', timeout)

        if (self.hostid in [srchost, dsthost]):
            mig_thread = utils.InterruptedThread(migrate_wrap, (vms_name,
                                                                srchost,
                                                                dsthost,
                                                                start_work,
                                                                check_work,
                                                                params_append))
        else:
            mig_thread = utils.InterruptedThread(wait_wrap, (vms_name,
                                                             srchost,
                                                             dsthost))
        mig_thread.start()
        return mig_thread

    def migrate_wait(self, vms_name, srchost, dsthost, start_work=None,
                     check_work=None, mig_mode="tcp", params_append=None):
        """
        Migrate machine from srchost to dsthost and wait for finish.
        It executes start_work on source machine before migration and executes
        check_work on dsthost after migration.

        :param vms_name: List of vms.
        :param srchost: src host id.
        :param dsthost: dst host id.
        :param start_work: Function which is started before migration.
        :param check_work: Function which is started after
                           done of migration.
        """
        self.migrate(vms_name, srchost, dsthost, start_work, check_work,
                     mig_mode, params_append).join()

    def cleanup(self):
        """
        Cleanup env after test.
        """
        if self.clone_master:
            self.sync_server.close()
            self.postprocess_env()

    def run(self):
        """
        Start multihost migration scenario.
        After scenario is finished or if scenario crashed it calls postprocess
        machines and cleanup env.
        """
        try:
            self.migration_scenario()

            self._hosts_barrier(self.hosts, self.hosts, 'all_test_finihed',
                                self.finish_timeout)
        finally:
            self.cleanup()


class MultihostMigrationFd(MultihostMigration):

    def __init__(self, test, params, env, preprocess_env=True):
        super(MultihostMigrationFd, self).__init__(test, params, env,
                                                   preprocess_env)

    def migrate_vms_src(self, mig_data):
        """
        Migrate vms source.

        :param mig_Data: Data for migration.

        For change way how machine migrates is necessary
        re implement this method.
        """
        def mig_wrapper(vm, cancel_delay, mig_offline, dsthost, vm_ports,
                        not_wait_for_migration, fd):
            vm.migrate(cancel_delay=cancel_delay, offline=mig_offline,
                       dest_host=dsthost,
                       not_wait_for_migration=not_wait_for_migration,
                       protocol="fd",
                       fd_src=fd)

            self.post_migration(vm, cancel_delay, mig_offline, dsthost,
                                vm_ports, not_wait_for_migration, fd, mig_data)

        logging.info("Start migrating now...")
        cancel_delay = mig_data.params.get("cancel_delay")
        if cancel_delay is not None:
            cancel_delay = int(cancel_delay)
        not_wait_for_migration = mig_data.params.get("not_wait_for_migration")
        if not_wait_for_migration == "yes":
            not_wait_for_migration = True
        mig_offline = mig_data.params.get("mig_offline")
        if mig_offline == "yes":
            mig_offline = True
        else:
            mig_offline = False

        multi_mig = []
        for vm in mig_data.vms:
            fd = vm.params.get("migration_fd")
            multi_mig.append((mig_wrapper, (vm, cancel_delay, mig_offline,
                                            mig_data.dst, mig_data.vm_ports,
                                            not_wait_for_migration,
                                            fd)))
        utils_misc.parallel(multi_mig)

    def _check_vms_source(self, mig_data):
        start_mig_tout = mig_data.params.get("start_migration_timeout", None)
        if start_mig_tout is None:
            for vm in mig_data.vms:
                vm.wait_for_login(timeout=self.login_timeout)
        self._hosts_barrier(mig_data.hosts, mig_data.mig_id,
                            'prepare_VMS', 60)

    def _check_vms_dest(self, mig_data):
        self._hosts_barrier(mig_data.hosts, mig_data.mig_id,
                            'prepare_VMS', 120)
        for vm in mig_data.vms:
            fd = vm.params.get("migration_fd")
            os.close(fd)

    def _connect_to_server(self, host, port, timeout=60):
        """
        Connect to network server.
        """
        endtime = time.time() + timeout
        sock = None
        while endtime > time.time():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((host, port))
                break
            except socket.error, err:
                (code, _) = err
                if (code != errno.ECONNREFUSED):
                    raise
                time.sleep(1)

        return sock

    def _create_server(self, port, timeout=60):
        """
        Create network server.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.bind(('', port))
        sock.listen(1)
        return sock

    def migrate_wait(self, vms_name, srchost, dsthost, start_work=None,
                     check_work=None, mig_mode="fd", params_append=None):
        vms_count = len(vms_name)
        mig_ports = []

        if self.params.get("hostid") == srchost:
            last_port = 5199
            for _ in range(vms_count):
                last_port = utils_misc.find_free_port(last_port + 1, 6000)
                mig_ports.append(last_port)

        sync = SyncData(self.master_id(), self.hostid,
                        self.params.get("hosts"),
                        {'src': srchost, 'dst': dsthost,
                         'port': "ports"}, self.sync_server)

        mig_ports = sync.sync(mig_ports, timeout=120)
        mig_ports = mig_ports[srchost]
        logging.debug("Migration port %s" % (mig_ports))

        if self.params.get("hostid") != srchost:
            sockets = []
            for mig_port in mig_ports:
                sockets.append(self._connect_to_server(srchost, mig_port))
            try:
                fds = {}
                for s, vm_name in zip(sockets, vms_name):
                    fds["migration_fd_%s" % vm_name] = s.fileno()
                logging.debug("File descrtiptors %s used for"
                              " migration." % (fds))

                super_cls = super(MultihostMigrationFd, self)
                super_cls.migrate_wait(vms_name, srchost, dsthost,
                                       start_work=start_work, mig_mode="fd",
                                       params_append=fds)
            finally:
                for s in sockets:
                    s.close()
        else:
            sockets = []
            for mig_port in mig_ports:
                sockets.append(self._create_server(mig_port))
            try:
                conns = []
                for s in sockets:
                    conns.append(s.accept()[0])
                fds = {}
                for conn, vm_name in zip(conns, vms_name):
                    fds["migration_fd_%s" % vm_name] = conn.fileno()
                logging.debug("File descrtiptors %s used for"
                              " migration." % (fds))

                # Prohibits descriptor inheritance.
                for fd in fds.values():
                    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
                    flags |= fcntl.FD_CLOEXEC
                    fcntl.fcntl(fd, fcntl.F_SETFD, flags)

                super_cls = super(MultihostMigrationFd, self)
                super_cls.migrate_wait(vms_name, srchost, dsthost,
                                       start_work=start_work, mig_mode="fd",
                                       params_append=fds)
                for conn in conns:
                    conn.close()
            finally:
                for s in sockets:
                    s.close()


class MultihostMigrationExec(MultihostMigration):

    def __init__(self, test, params, env, preprocess_env=True):
        super(MultihostMigrationExec, self).__init__(test, params, env,
                                                     preprocess_env)

    def post_migration(self, vm, cancel_delay, mig_offline, dsthost,
                       mig_exec_cmd, not_wait_for_migration, fd,
                       mig_data):
        if mig_data.params.get("host_mig_offline") == "yes":
            src_tmp = vm.params.get("migration_sfiles_path")
            dst_tmp = vm.params.get("migration_dfiles_path")
            username = vm.params.get("username")
            password = vm.params.get("password")
            remote.scp_to_remote(dsthost, "22", username, password,
                                 src_tmp, dst_tmp)

    def migrate_vms_src(self, mig_data):
        """
        Migrate vms source.

        :param mig_Data: Data for migration.

        For change way how machine migrates is necessary
        re implement this method.
        """
        def mig_wrapper(vm, cancel_delay, mig_offline, dsthost, mig_exec_cmd,
                        not_wait_for_migration, mig_data):
            vm.migrate(cancel_delay=cancel_delay,
                       offline=mig_offline,
                       dest_host=dsthost,
                       not_wait_for_migration=not_wait_for_migration,
                       protocol="exec",
                       migration_exec_cmd_src=mig_exec_cmd)

            self.post_migration(vm, cancel_delay, mig_offline,
                                dsthost, mig_exec_cmd,
                                not_wait_for_migration, None, mig_data)

        logging.info("Start migrating now...")
        cancel_delay = mig_data.params.get("cancel_delay")
        if cancel_delay is not None:
            cancel_delay = int(cancel_delay)
        not_wait_for_migration = mig_data.params.get("not_wait_for_migration")
        if not_wait_for_migration == "yes":
            not_wait_for_migration = True
        mig_offline = mig_data.params.get("mig_offline")
        if mig_offline == "yes":
            mig_offline = True
        else:
            mig_offline = False

        multi_mig = []
        for vm in mig_data.vms:
            mig_exec_cmd = vm.params.get("migration_exec_cmd_src")
            multi_mig.append((mig_wrapper, (vm, cancel_delay,
                                            mig_offline,
                                            mig_data.dst,
                                            mig_exec_cmd,
                                            not_wait_for_migration,
                                            mig_data)))
        utils_misc.parallel(multi_mig)

    def _check_vms_source(self, mig_data):
        start_mig_tout = mig_data.params.get("start_migration_timeout", None)
        if start_mig_tout is None:
            for vm in mig_data.vms:
                vm.wait_for_login(timeout=self.login_timeout)

        if mig_data.params.get("host_mig_offline") != "yes":
            self._hosts_barrier(mig_data.hosts, mig_data.mig_id,
                                'prepare_VMS', 60)

    def _check_vms_dest(self, mig_data):
        if mig_data.params.get("host_mig_offline") != "yes":
            self._hosts_barrier(mig_data.hosts, mig_data.mig_id,
                                'prepare_VMS', 120)

    def migrate_wait(self, vms_name, srchost, dsthost, start_work=None,
                     check_work=None, mig_mode="exec", params_append=None):
        vms_count = len(vms_name)
        mig_ports = []

        host_offline_migration = self.params.get("host_mig_offline")

        sync = SyncData(self.master_id(), self.hostid,
                        self.params.get("hosts"),
                        {'src': srchost, 'dst': dsthost,
                         'port': "ports"}, self.sync_server)

        mig_params = {}

        if host_offline_migration != "yes":
            if self.params.get("hostid") == dsthost:
                last_port = 5199
                for _ in range(vms_count):
                    last_port = utils_misc.find_free_port(last_port + 1, 6000)
                    mig_ports.append(last_port)

            mig_ports = sync.sync(mig_ports, timeout=120)
            mig_ports = mig_ports[dsthost]
            logging.debug("Migration port %s" % (mig_ports))
            mig_cmds = {}
            for mig_port, vm_name in zip(mig_ports, vms_name):
                mig_dst_cmd = "nc -l %s %s" % (dsthost, mig_port)
                mig_src_cmd = "nc %s %s" % (dsthost, mig_port)
                mig_params["migration_exec_cmd_src_%s" %
                           (vm_name)] = mig_src_cmd
                mig_params["migration_exec_cmd_dst_%s" %
                           (vm_name)] = mig_dst_cmd
        else:
            # Generate filenames for migration.
            mig_fnam = {}
            for vm_name in vms_name:
                while True:
                    fnam = ("mig_" + utils.generate_random_string(6) +
                            "." + vm_name)
                    fpath = os.path.join(self.test.tmpdir, fnam)
                    if (fnam not in mig_fnam.values() and
                            not os.path.exists(fnam)):
                        mig_fnam[vm_name] = fpath
                        break
            mig_fs = sync.sync(mig_fnam, timeout=120)
            mig_cmds = {}
            # Prepare cmd and files.
            if self.params.get("hostid") == srchost:
                mig_src_cmd = "gzip -c > %s"
                for vm_name in vms_name:
                    mig_params["migration_sfiles_path_%s" % (vm_name)] = (
                        mig_fs[srchost][vm_name])
                    mig_params["migration_dfiles_path_%s" % (vm_name)] = (
                        mig_fs[dsthost][vm_name])

                    mig_params["migration_exec_cmd_src_%s" % (vm_name)] = (
                        mig_src_cmd % mig_fs[srchost][vm_name])

            if self.params.get("hostid") == dsthost:
                mig_dst_cmd = "gzip -c -d %s"
                for vm_name in vms_name:
                    mig_params["migration_exec_cmd_dst_%s" % (vm_name)] = (
                        mig_dst_cmd % mig_fs[dsthost][vm_name])

        logging.debug("Exec commands %s", mig_cmds)

        super_cls = super(MultihostMigrationExec, self)
        super_cls.migrate_wait(vms_name, srchost, dsthost,
                               start_work=start_work, mig_mode=mig_mode,
                               params_append=mig_params)


class GuestSuspend(object):

    """
    Suspend guest, supports both Linux and Windows.

    """
    SUSPEND_TYPE_MEM = "mem"
    SUSPEND_TYPE_DISK = "disk"

    def __init__(self, params, vm):
        if not params or not vm:
            raise error.TestError("Missing 'params' or 'vm' parameters")

        self._open_session_list = []
        self.vm = vm
        self.params = params
        self.login_timeout = float(self.params.get("login_timeout", 360))
        self.services_up_timeout = float(self.params.get("services_up_timeout",
                                                         30))
        self.os_type = self.params.get("os_type")

    def _get_session(self):
        self.vm.verify_alive()
        session = self.vm.wait_for_login(timeout=self.login_timeout)
        return session

    def _session_cmd_close(self, session, cmd):
        try:
            return session.cmd_status_output(cmd)
        finally:
            try:
                session.close()
            except Exception:
                pass

    def _cleanup_open_session(self):
        try:
            for s in self._open_session_list:
                if s:
                    s.close()
        except Exception:
            pass

    @error.context_aware
    def setup_bg_program(self, **args):
        """
        Start up a program as a flag in guest.
        """
        suspend_bg_program_setup_cmd = args.get("suspend_bg_program_setup_cmd")

        error.context("Run a background program as a flag", logging.info)
        session = self._get_session()
        self._open_session_list.append(session)

        logging.debug("Waiting all services in guest are fully started.")
        time.sleep(self.services_up_timeout)

        session.sendline(suspend_bg_program_setup_cmd)

    @error.context_aware
    def check_bg_program(self, **args):
        """
        Make sure the background program is running as expected
        """
        suspend_bg_program_chk_cmd = args.get("suspend_bg_program_chk_cmd")

        error.context("Verify background program is running", logging.info)
        session = self._get_session()
        s, _ = self._session_cmd_close(session, suspend_bg_program_chk_cmd)
        if s:
            raise error.TestFail("Background program is dead. Suspend failed.")

    @error.context_aware
    def kill_bg_program(self, **args):
        error.context("Kill background program after resume")
        suspend_bg_program_kill_cmd = args.get("suspend_bg_program_kill_cmd")

        try:
            session = self._get_session()
            self._session_cmd_close(session, suspend_bg_program_kill_cmd)
        except Exception, e:
            logging.warn("Could not stop background program: '%s'", e)
            pass

    @error.context_aware
    def _check_guest_suspend_log(self, **args):
        error.context("Check whether guest supports suspend",
                      logging.info)
        suspend_support_chk_cmd = args.get("suspend_support_chk_cmd")

        session = self._get_session()
        s, o = self._session_cmd_close(session, suspend_support_chk_cmd)

        return s, o

    def verify_guest_support_suspend(self, **args):
        s, _ = self._check_guest_suspend_log(**args)
        if s:
            raise error.TestError("Guest doesn't support suspend.")

    @error.context_aware
    def start_suspend(self, **args):
        suspend_start_cmd = args.get("suspend_start_cmd")
        error.context("Start suspend [%s]" % (suspend_start_cmd), logging.info)

        session = self._get_session()
        self._open_session_list.append(session)

        # Suspend to disk
        session.sendline(suspend_start_cmd)

    @error.context_aware
    def verify_guest_down(self, **args):
        # Make sure the VM goes down
        error.context("Wait for guest goes down after suspend")
        suspend_timeout = 240 + int(self.params.get("smp")) * 60
        if not utils_misc.wait_for(self.vm.is_dead, suspend_timeout, 2, 2):
            raise error.TestFail("VM refuses to go down. Suspend failed.")

    @error.context_aware
    def resume_guest_mem(self, **args):
        error.context("Resume suspended VM from memory")
        self.vm.monitor.system_wakeup()

    @error.context_aware
    def resume_guest_disk(self, **args):
        error.context("Resume suspended VM from disk")
        self.vm.create()

    @error.context_aware
    def verify_guest_up(self, **args):
        error.context("Verify guest system log", logging.info)
        suspend_log_chk_cmd = args.get("suspend_log_chk_cmd")

        session = self._get_session()
        s, o = self._session_cmd_close(session, suspend_log_chk_cmd)
        if s:
            raise error.TestError("Could not find suspend log. [%s]" % (o))

    @error.context_aware
    def action_before_suspend(self, **args):
        error.context("Actions before suspend")
        pass

    @error.context_aware
    def action_during_suspend(self, **args):
        error.context("Sleep a while before resuming guest", logging.info)

        time.sleep(10)
        if self.os_type == "windows":
            # Due to WinXP/2003 won't suspend immediately after issue S3 cmd,
            # delay 10~60 secs here, maybe there's a bug in windows os.
            logging.info("WinXP/2003 need more time to suspend, sleep 50s.")
            time.sleep(50)

    @error.context_aware
    def action_after_suspend(self, **args):
        error.context("Actions after suspend")
        pass
