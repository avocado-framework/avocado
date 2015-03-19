#!/usr/bin/python

from avocado import api

class DataDirTest(api.Test):

    """
    Test that uses resources from the data dir.
    """

    default_params = {'source': 'datadir.c'}

    def setup(self):
        """
        Build 'datadir'.
        """
        c_file = self.get_data_path(self.params.source)
        c_file_name = api.path.basename(c_file)
        dest_c_file = api.path.join(self.srcdir, c_file_name)
        api.copy(c_file, dest_c_file)
        api.make(self.srcdir,
                 env={'CFLAGS': '-g -O0'},
                 extra_args='datadir')

    def action(self):
        """
        Execute 'datadir'.
        """
        cmd = api.path.join(self.srcdir, 'datadir')
        cmd_result = api.run(cmd)
        self.log.info(cmd_result)


if __name__ == "__main__":
    api.main()
