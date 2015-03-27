#!/usr/bin/python

from avocado import api


class SyncTest(api.Test):

    """
    Execute the synctest test suite.
    """
    default_params = {'sync_tarball': 'synctest.tar.bz2',
                      'sync_length': 100,
                      'sync_loop': 10,
                      'debug_symbols': True}

    def setup(self):
        """
        Build the synctest suite.
        """
        self.cwd = api.getcwd()
        tarball_path = self.get_data_path(self.params.sync_tarball)
        api.extract(tarball_path, self.srcdir)
        self.srcdir = api.path.join(self.srcdir, 'synctest')
        if self.params.debug_symbols:
            api.make(self.srcdir,
                     env={'CFLAGS': '-g -O0'},
                     extra_args='synctest')
        else:
            api.make(self.srcdir)

    def action(self):
        """
        Execute synctest with the appropriate params.
        """
        api.chdir(self.srcdir)
        path = api.path.join(api.getcwd(), 'synctest')
        cmd = ('%s %s %s' %
               (path, self.params.sync_length, self.params.sync_loop))
        api.system(cmd)
        api.chdir(self.cwd)


if __name__ == "__main__":
    api.main()
