import os
import pwd

from avocado import Test


class FileByAnsible(Test):
    """
    :avocado: dependency={"type": "ansible-module", "uri": "file", "path": "/tmp/ansible_tmp", "state": "touch"}
    """

    def test(self):
        files = os.listdir("/tmp")
        self.log.info(files)
        if not "ansible_tmp" in files:
            self.fail("Did not find an ansible created file")


class UserByAnsible(Test):
    """
    :avocado: dependency={"type": "ansible-module", "uri": "user", "name": "test-user"}
    """

    def test(self):
        users = pwd.getpwall()
        self.log.info(users)
        for user in users:
            if user.pw_name == "test-user":
                return
        self.fail("Did not find an ansible created user")
