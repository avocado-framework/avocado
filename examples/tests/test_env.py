import os
import sys

from avocado import Test
from avocado.utils import genio


class Env(Test):

    def test(self):
        """
        Logs information about the environment under which the test is executed
        """
        pid = os.getpid()
        p_dir = '/proc/%d' % pid

        def get_proc_content(rel_path):
            try:
                return genio.read_file(os.path.join(p_dir, rel_path)).strip()
            except OSError:
                return "<NOT AVAILABLE>"

        self.log.debug('Process ID: %s', pid)
        self.log.debug('Current workding directory: %s', os.getcwd())
        self.log.debug('Process "name" (comm): %s', get_proc_content('comm'))
        raw_cmdline = get_proc_content('cmdline')
        massaged_cmdline = raw_cmdline.replace('\0', ' ')
        self.log.debug('Process "cmdline": %s', massaged_cmdline)

        def log_std_io(name, std_io):
            self.log.debug('%s:', name.upper())
            self.log.debug(' sys.%s: %s', name, std_io)
            self.log.debug(' sys.%s is a tty: %s', name, std_io.isatty())
            if hasattr(std_io, 'fileno'):
                self.log.debug(' fd: %s', std_io.fileno())
                self.log.debug(' fd is tty: %s', os.isatty(std_io.fileno()))
            else:
                self.log.debug(' fd: not available')
                self.log.debug(' fd is a tty: can not determine, most possibly *not* a tty')

        log_std_io('stdin', sys.stdin)
        log_std_io('stdout', sys.stdout)
        log_std_io('stderr', sys.stdout)

        fd_dir = '/proc/%s/fd' % pid
        if os.path.isdir('/proc/%s/fd' % pid):
            fds = os.listdir(fd_dir)
            self.log.debug('Open file descriptors:')
            for fd in fds:
                fd_path = os.path.join(fd_dir, fd)
                if os.path.islink(fd_path):
                    self.log.debug(" %s: %s", fd, os.readlink(fd_path))

        self.log.debug('Environment variables (probably) set by Avocado:')
        for k, v in os.environ.items():
            if k.startswith('AVOCADO_'):
                self.log.debug(' %s: %s', k, v)
