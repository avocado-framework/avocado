import os
import shutil
import tempfile

from avocado import Test
from avocado.utils import script
from avocado.utils import process

CLEAN_TEST = """import os
from avocado import Test

class Clean(Test):
    def test(self):
        path = os.path.expanduser("~/.avocado-has-not-touched-me")
        self.assertFalse(os.path.exists(path))
"""


DIRTY_TEST = """import os
from avocado import Test

class Dirty(Test):
    def test(self):
        self.touch(os.path.expanduser("~/.avocado-has-not-touched-me"))

    @staticmethod
    def touch(name):
        with open(name, 'w'):
            os.utime(name, None)
"""


class VMCleanup(Test):

    """
    Tests the Avocado VM plugin `--vm-cleanup` feature

    The approach chosen here is to have a first run of Avocado making sure that
    a flag file does not exist. A second run of Avocado, now executed with an
    additional `--vm-cleanup` parameter runs a test that creates the flag file.
    Finally, the third and last execution of re-runs the same test as the first
    run, checking that the flag file does *not* exist, that is, the clean up of
    the VM did work.

    Because this test requires a libvirt domain and the hostname/address of
    that virtual machine, these parameters assume no defaults for safety and/or
    security causes. Please edit the vm-cleanup.yaml file with the appropriate
    parameters.
    """

    def setUp(self):
        vm_domain = self.params.get("vm_domain", default=None)
        vm_host = self.params.get("vm_host", default=None)
        if vm_domain is None or vm_host is None:
            self.skip('Either "vm_domain" or "vm_host" parameters have not '
                      'been given. Please edit the "vm-cleanup.yaml" file '
                      'with the appropriate parameters')

        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        clean_test = os.path.join(self.tmpdir, 'clean.py')
        self.clean_test_path = script.make_script(clean_test, CLEAN_TEST)
        dirty_test = os.path.join(self.tmpdir, 'dirty.py')
        self.dirty_test_path = script.make_script(dirty_test, DIRTY_TEST)

    def test(self):
        vm_domain = self.params.get("vm_domain", default=None)
        vm_host = self.params.get("vm_host", default=None)
        vm_username = self.params.get("vm_username", default=None)
        vm_password = self.params.get("vm_password", default=None)

        cmd = ('avocado run --sysinfo=off --job-results-dir %s --vm-domain=%s '
               '--vm-host=%s')
        cmd %= (self.tmpdir, vm_domain, vm_host)
        if vm_username:
            cmd += ' --vm-username=%s' % vm_username
        if vm_password:
            cmd += ' --vm-password=%s' % vm_password

        cmd_clean = '%s %s' % (cmd, self.clean_test_path)
        cmd_dirty = '%s --vm-cleanup %s' % (cmd, self.dirty_test_path)

        process.run(cmd_clean)
        process.run(cmd_dirty)
        process.run(cmd_clean)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
