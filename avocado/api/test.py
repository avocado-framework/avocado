import os
from avocado.api import data_dir

class Test(object):

    """
    Represents an avocado test.
    """

    def __init__(self, params, options):
        self.bindir = data_dir.get_root_dir()
        self.srcdir = os.path.join(self.bindir, 'src')
        if not os.path.isdir(self.srcdir):
            os.makedirs(self.srcdir)

        self.tmpdir = os.path.join(self.bindir, 'tmp')
        if not os.path.isdir(self.tmpdir):
            os.makedirs(self.tmpdir)

        self.debugdir = None
        self.outputdir = None
        self.resultsdir = None
        self.logfile = None
        self.file_handler = None

    def set_debugdir(self, debugdir):
        self.debugdir = os.path.join(debugdir, self.tag)
        self.outputdir = self.debugdir
        if not os.path.isdir(self.debugdir):
            os.makedirs(self.debugdir)
        self.resultsdir = os.path.join(self.debugdir, 'results')
        if not os.path.isdir(self.resultsdir):
            os.makedirs(self.resultsdir)
        self.profdir = os.path.join(self.resultsdir, 'profiling')
        if not os.path.isdir(self.profdir):
            os.makedirs(self.profdir)
        self.logfile = os.path.join(self.debugdir, 'debug.log')

    def run_once(self):
        test_passed = True
        return test_passed