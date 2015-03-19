#!/usr/bin/python

from avocado import api

class CAbort(api.Test):

    """
    A test that calls C standard lib function abort().
    """

    default_params = {'source': 'abort.c'}

    def setup(self):
        """
        Build 'abort'.
        """
        c_file = self.get_data_path(self.params.source)
        c_file_name = api.path.basename(c_file)
        dest_c_file = api.path.join(self.srcdir, c_file_name)
        api.copy(c_file, dest_c_file)
        api.make(self.srcdir,
                 env={'CFLAGS': '-g -O0'},
                 extra_args='abort')

    def action(self):
        """
        Execute 'abort'.
        """
        cmd = api.path.join(self.srcdir, 'abort')
        cmd_result = api.run(cmd, ignore_status=True)
        self.log.info(cmd_result)
        expected_result = -6  # SIGABRT = 6
        self.assertEqual(cmd_result.exit_status, expected_result)


if __name__ == "__main__":
    api.main()
