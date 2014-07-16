"""
Base avocado Environment class enhanced with methods used by virt tests.
"""

import copy
import glob
import os
import re
import shutil
import logging
import time
import threading

log = logging.getLogger("avocado.test")

try:
    import PIL.Image
except ImportError:
    log.warning('No python imaging library installed. PPM image '
                'conversion to JPEG disabled. In order to enable it, '
                'please install python-imaging or the equivalent for your '
                'distro.')

from avocado import env
from avocado import aexpect
from avocado import machine
from avocado.core import data_dir
from avocado.utils import misc
from avocado.utils import crypto
from avocado.utils import remote

from avocado.virt import ppm_utils
from avocado.virt import address_cache
from avocado.virt import exceptions as virt_exceptions
from avocado.virt import storage
from avocado.virt import video_maker
from avocado.virt.utils import network
from avocado.virt.qemu import monitor
from avocado.virt.qemu import storage as qemu_storage


class Env(env.Env):

    def __init__(self, filename=None, version=0, params=None, test=None):
        env.Env.__init__(self, filename, version)
        self.params = params
        self.test = test
        self.address_cache = address_cache.AddressCache(env=self)
        self.screendump_thread = None
        self.screendump_thread_termination = None

    def get_vm(self, name):
        return self.get_object("vm", name)

    def get_all_vms(self):
        return self.get_all_objects("vm")

    def _take_screendumps(self):
        temp_dir = self.test.logdir

        temp_filename = os.path.join(temp_dir, "scrdump-%s.ppm" %
                                     crypto.get_random_string(6))
        delay = float(self.params.get("screendump_delay", 5))
        quality = int(self.params.get("screendump_quality", 30))
        inactivity_treshold = float(self.params.get("inactivity_treshold", 1800))
        inactivity_watcher = self.params.get("inactivity_watcher", "log")

        cache = {}
        counter = {}
        inactivity = {}

        while True:
            for vm in self.get_all_vms():
                if vm.instance not in counter.keys():
                    counter[vm.instance] = 0
                if vm.instance not in inactivity.keys():
                    inactivity[vm.instance] = time.time()
                if not vm.is_alive():
                    continue
                vm_pid = vm.get_pid()
                try:
                    vm.screendump(filename=temp_filename, debug=False)
                except monitor.MonitorError, e:
                    log.warn(e)
                    continue
                except AttributeError, e:
                    log.warn(e)
                    continue
                if not os.path.exists(temp_filename):
                    log.warn("VM '%s' failed to produce a screendump",
                             vm.name)
                    continue
                if not ppm_utils.image_verify_ppm_file(temp_filename):
                    log.warn("VM '%s' produced an invalid screendump",
                             vm.name)
                    os.unlink(temp_filename)
                    continue
                screendump_dir = os.path.join(self.test.debugdir,
                                              "screendumps_%s_%s" % (vm.name,
                                                                     vm_pid))
                try:
                    os.makedirs(screendump_dir)
                except OSError:
                    pass
                counter[vm.instance] += 1
                screendump_filename = os.path.join(screendump_dir, "%04d.jpg" %
                                                   counter[vm.instance])
                vm.verify_bsod(screendump_filename)
                image_hash = crypto.hash_file(temp_filename)
                if image_hash in cache:
                    time_inactive = time.time() - inactivity[vm.instance]
                    if time_inactive > inactivity_treshold:
                        msg = (
                            "%s screen is inactive for more than %d s (%d min)" %
                            (vm.name, time_inactive, time_inactive / 60))
                        if inactivity_watcher == "error":
                            try:
                                raise virt_exceptions.VMScreenInactiveError(vm,
                                                                            time_inactive)
                            except virt_exceptions.VMScreenInactiveError:
                                log.error(msg)
                                # Let's reset the counter
                                inactivity[vm.instance] = time.time()
                                #self.test.background_errors.put(sys.exc_info())
                        elif inactivity_watcher == 'log':
                            log.debug(msg)
                    try:
                        os.link(cache[image_hash], screendump_filename)
                    except OSError:
                        pass
                else:
                    inactivity[vm.instance] = time.time()
                    try:
                        try:
                            image = PIL.Image.open(temp_filename)
                            image.save(screendump_filename, format="JPEG",
                                       quality=quality)
                            cache[image_hash] = screendump_filename
                        except IOError, error_detail:
                            log.warning("VM '%s' failed to produce a "
                                        "screendump: %s", vm.name,
                                        error_detail)
                            # Decrement the counter as we in fact failed to
                            # produce a converted screendump
                            counter[vm.instance] -= 1
                    except NameError:
                        pass
                os.unlink(temp_filename)

            if self.screendump_thread_termination.isSet():
                self.screendump_thread_termination = None
                break
            self.screendump_thread_termination.wait(delay)

    def pre_process(self):
        if self.params.get('requires_root', 'no') == 'yes':
            misc.verify_running_as_root()
        self.address_cache.start(self.params)

        requested_vms = self.params.objects("vms")
        for key in self.get_all_vms():
            vm = self[key]
            if vm.name not in requested_vms:
                vm.destroy()
                del self[key]

        # Preprocess all VMs and images
        if not self.params.get("skip_preprocess", "yes") == "yes":
            self.process()

        # Start screendump thread
        self.screendump_thread = threading.Thread(target=self._take_screendumps,
                                                  name='Screendump')
        self.screendump_thread.start()
        self.screendump_thread_termination = threading.Event()

    def pre_process_image(self, test, params, image_name):
        """
        Preprocess a single QEMU image according to the instructions in params.

        :param test: Autotest test object.
        :param params: A dict containing image preprocessing parameters.
        :param vm_process_status: This is needed in postprocess_image. Add it here
                                  only for keep it work with process_images()
        :note: Currently this function just creates an image if requested.
        """
        base_dir = params.get("images_base_dir", data_dir.get_data_dir())

        if not storage.base.preprocess_image_backend(base_dir, params,
                                                     image_name):
            logging.error("Backend can't be prepared correctly.")

        image_filename = storage.base.get_image_filename(params,
                                                         base_dir)

        create_image = False
        if params.get("force_create_image") == "yes":
            create_image = True
        elif (params.get("create_image") == "yes" and not
              storage.base.file_exists(params, image_filename)):
            create_image = True

        if params.get("backup_image_before_testing", "no") == "yes":
            image = qemu_storage.QemuImg(params, base_dir, image_name)
            image.backup_image(params, base_dir, "backup", True, True)
        if create_image:
            image = qemu_storage.QemuImg(params, base_dir, image_name)
            image.create(params)

    def pre_process_vm(self, test, params, name):
        """
        Preprocess a single VM object according to the instructions in params.
        Start the VM if requested and get a screendump.

        :param test: An Autotest test object.
        :param params: A dict containing VM preprocessing parameters.
        :param env: The environment (a dict-like object).
        :param name: The name of the VM object.
        """
        print name
        vm = self.get_vm(name)
        vm_type = self.params.get('vm_type')
        target = self.params.get('target')

        create_vm = False
        if not vm:
            create_vm = True
        else:
            pass
        if create_vm:
            vm = self.create_vm(vm_type, target, name, self.params, test.workdir)

        old_vm = copy.copy(vm)

        remove_vm = False
        if params.get("force_remove_vm") == "yes":
            remove_vm = True

        if remove_vm:
            vm.remove()

        start_vm = False
        update_virtnet = False
        gracefully_kill = params.get("kill_vm_gracefully") == "yes"

        if params.get("migration_mode"):
            start_vm = True

        elif params.get("start_vm") == "yes":
            if not vm.is_alive():
                start_vm = True
            if params.get("check_vm_needs_restart", "yes") == "yes":
                if vm.needs_restart():
                    vm.devices = None
                    start_vm = True
                    old_vm.destroy(gracefully=gracefully_kill)
                    update_virtnet = True

        if start_vm:
            if update_virtnet:
                vm.update_vm_id()
                vm.virtnet = network.VirtNet(params, name, vm.instance)
            # Start the VM (or restart it if it's already up)
            if params.get("reuse_previous_config", "no") == "no":
                vm.create()
            else:
                vm.create()

        elif not vm.is_alive():  # VM is dead and won't be started, update params
            vm.devices = None
            vm.params = params
        else:
            # Only work when parameter 'start_vm' is no and VM is alive
            if (params.get("kill_vm_before_test") == "yes" and
                    params.get("start_vm") == "no"):
                old_vm.destroy(gracefully=gracefully_kill)
            else:
                # VM is alive and we just need to open the serial console
                vm.create_serial_console()

        pause_vm = False

        if params.get("paused_after_start_vm") == "yes":
            pause_vm = True
            # Check the status of vm
            if (not vm.is_alive()) or (vm.is_paused()):
                pause_vm = False

        if pause_vm:
            vm.pause()

    def _call_vm_func(self, test, params):
        for vm_name in params.objects("vms"):
            vm_params = params.object_params(vm_name)
            self.pre_process_vm(test, vm_params, vm_name)

    def _call_image_func(self, test, params):
        if params.get("skip_image_processing") == "yes":
            return

        if params.objects("vms"):
            for vm_name in params.objects("vms"):
                vm_params = params.object_params(vm_name)
                vm = self.get_vm(vm_name)
                unpause_vm = False
                if vm is None or vm.is_dead():
                    vm_process_status = 'dead'
                else:
                    vm_process_status = 'running'
                if vm is not None and vm.is_alive() and not vm.is_paused():
                    vm.pause()
                    unpause_vm = True
                    vm_params['skip_cluster_leak_warn'] = "yes"
                try:
                    self.process_images(self.pre_process_image, test,
                                        vm_params,
                                        vm_process_status)
                finally:
                    if unpause_vm:
                        vm.resume()
        else:
            self.process_images(self.pre_process_image, test, params)

    def create_vm(self, vm_type, target, name, params, bindir):
        """
        Create and register a VM in this Env object
        """
        vm_class = machine.mapping[params.get('vm_type')]
        if vm_class is not None:
            vm = vm_class(params, name)
            self.register_vm(name, vm)
            return vm

    def register_vm(self, name, vm):
        self.register_object('vm', name, vm)

    def process(self, test, params, vm_first):
        """
        Pre- or post-process VMs and images according to the instructions in params.
        Call image_func for each image listed in params and vm_func for each VM.

        :param test: An Autotest test object.
        :param params: A dict containing all VM and image parameters.
        :param env: The environment (a dict-like object).
        :param image_func: A function to call for each image.
        :param vm_func: A function to call for each VM.
        :param vm_first: Call vm_func first or not.
        """
        if not vm_first:
            self._call_image_func(test, params)

        self._call_vm_func(test, params)

        if vm_first:
            self._call_image_func(test, params)

    def post_process(self, test, params):
        """
        Postprocess all VMs and images according to the instructions in params.

        :param test: An Autotest test object.
        :param params: Dict containing all VM and image parameters.
        """
        err = ""

        # Postprocess all VMs and images
        try:
            self.process(test, params, vm_first=True)
        except Exception, details:
            err += "\nPostprocess: %s" % str(details).replace('\\n', '\n  ')
            logging.error(details)

        # Terminate the screendump thread
        self.screendump_thread_termination_event.set()
        self.screendump_thread.join(10)

        # Encode an HTML 5 compatible video from the screenshots produced

        dirs = re.findall("(screendump\S*_[0-9]+)", str(os.listdir(test.debugdir)))
        for _ in dirs:
            screendump_dir = os.path.join(test.debugdir, dir)
            if (params.get("encode_video_files", "yes") == "yes" and
                    glob.glob("%s/*" % screendump_dir)):
                try:
                    video = video_maker.GstPythonVideoMaker()
                    if (video.has_element('vp8enc') and video.has_element('webmmux')):
                        video_file = os.path.join(test.debugdir, "%s-%s.webm" %
                                                  (screendump_dir, test.iteration))
                    else:
                        video_file = os.path.join(test.debugdir, "%s-%s.ogg" %
                                                  (screendump_dir, test.iteration))
                    logging.debug("Encoding video file %s", video_file)
                    video.start(screendump_dir, video_file)

                except Exception, detail:
                    logging.info(
                        "Video creation failed for %s: %s", screendump_dir, detail)

        # Warn about corrupt PPM files
        for f in glob.glob(os.path.join(test.debugdir, "*.ppm")):
            if not ppm_utils.image_verify_ppm_file(f):
                logging.warn("Found corrupt PPM file: %s", f)

        # Should we convert PPM files to PNG format?
        if params.get("convert_ppm_files_to_png", "no") == "yes":
            try:
                for f in glob.glob(os.path.join(test.debugdir, "*.ppm")):
                    if ppm_utils.image_verify_ppm_file(f):
                        new_path = f.replace(".ppm", ".png")
                        image = PIL.Image.open(f)
                        image.save(new_path, format='PNG')
            except NameError:
                pass

        # Should we keep the PPM files?
        if params.get("keep_ppm_files", "no") != "yes":
            for f in glob.glob(os.path.join(test.debugdir, '*.ppm')):
                os.unlink(f)

        # Should we keep the screendump dirs?
        if params.get("keep_screendumps", "no") != "yes":
            for d in glob.glob(os.path.join(test.debugdir, "screendumps_*")):
                if os.path.isdir(d) and not os.path.islink(d):
                    shutil.rmtree(d, ignore_errors=True)

        # Should we keep the video files?
        if params.get("keep_video_files", "yes") != "yes":
            for f in (glob.glob(os.path.join(test.debugdir, '*.ogg')) +
                      glob.glob(os.path.join(test.debugdir, '*.webm'))):
                os.unlink(f)

        # Kill all unresponsive VMs
        if params.get("kill_unresponsive_vms") == "yes":
            for vm in self.get_all_vms():
                if vm.is_dead() or vm.is_paused():
                    continue
                try:
                    # Test may be fast, guest could still be booting
                    if len(vm.virtnet) > 0:
                        session = vm.wait_for_login(timeout=vm.LOGIN_WAIT_TIMEOUT)
                        session.close()
                    else:
                        session = vm.wait_for_serial_login(
                            timeout=vm.LOGIN_WAIT_TIMEOUT)
                        session.close()
                except (remote.LoginError, virt_exceptions.VMError, IndexError), e:
                    logging.warn(e)
                    vm.destroy(gracefully=False)

        # Kill VMs with deleted disks
        for vm in self.get_all_vms():
            destroy = False
            vm_params = params.object_params(vm.name)
            for image in vm_params.objects('images'):
                if params.object_params(image).get('remove_image') == 'yes':
                    destroy = True
            if destroy and not vm.is_dead():
                logging.debug('Image of VM %s was removed, destroing it.', vm.name)
                vm.destroy()

        # Terminate address cache process
        self.address_cache.stop()

        # Kill all aexpect tail threads
        aexpect.kill_tail_threads()

        living_vms = [vm for vm in self.get_all_vms() if vm.is_alive()]
        # Close all monitor socket connections of living vm.
        for vm in living_vms:
            if hasattr(vm, "monitors"):
                for m in vm.monitors:
                    try:
                        m.close()
                    except Exception:
                        pass
            # Close the serial console session, as it'll help
            # keeping the number of filedescriptors used by virt-test honest.
            vm.cleanup_serial_console()

        if err:
            raise virt_exceptions.VMError("Failures occurred while postprocess:%s" % err)
