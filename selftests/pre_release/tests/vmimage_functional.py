import os
import shutil

from avocado import Test, fail_on
from avocado.plugins import vmimage as vmimage_plug
from avocado.utils import process


class ImageFunctional(Test):
    @staticmethod
    def __get_cache_files():
        return set(i["file"] for i in vmimage_plug.list_downloaded_images())

    def setUp(self):
        self.vmimage_name = self.params.get("name", default="fedora")
        self.cache_files = self.__get_cache_files()

    @fail_on(process.CmdError)
    def test_get(self):
        process.run(f"avocado vmimage get --distro={self.vmimage_name}")

    def tearDown(self):
        dirty_files = self.__get_cache_files() - self.cache_files
        for file_path in dirty_files:
            shutil.rmtree(os.path.dirname(file_path))
