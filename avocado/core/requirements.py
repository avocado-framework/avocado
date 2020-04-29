
import argparse
import os

from . import data_dir
from . import safeloader
from ..utils.asset import Asset
from ..utils.vmimage import get as get_vmimage
from ..utils import data_structures


class RequirementsResolver:

    def __init__(self, references):
        self.references = references
        self.supported_requirements = {
            'file': self._handle_assets,
            'image': self._handle_vmimage,
        }

    @staticmethod
    def _extract_requirements_from_reference(test):
        requirements = []
        # work with enabled tests only (index 0)
        test_info = safeloader.find_avocado_tests(test)[0]
        for tests in test_info.values():
            for test in tests:
                # requirements are the 3rd item in the set
                requirements.extend(test[2])
        return requirements

    @staticmethod
    def _handle_assets(params):
        # set cache directory
        params['cache_dirs'] = data_dir.get_cache_dirs()
        # set algorithm
        algorithm = params.pop('algorithm', None)
        params['algorithm'] = algorithm
        # set expire
        expire = params.pop('expire', None)
        if expire is not None:
            params['expire'] = data_structures.time_to_seconds(str(expire))
        params['expire'] = expire

        # fetch asset
        try:
            print('Fulfilling file requirement: %s' % params['name'])
            asset_obj = Asset(**params)
            asset_destination = asset_obj.fetch()
            print(' File requirement: %s' % asset_destination)
        except (OSError, ValueError) as failed:
            print(failed)

    @staticmethod
    def _handle_vmimage(params):
        # set cache directory
        params['cache_dir'] = data_dir.get_cache_dirs()

        # download image
        try:
            print('Fulfilling image requirement: %s' % params['name'])
            vmimage_info = get_vmimage(**params)
            print(' Image requirement: %s' % vmimage_info.base_image)
        except AttributeError as failed:
            print(failed)

    def _resolve_from_docstring(self, test):
        # list of requirements in docstring format
        requirements = self._extract_requirements_from_reference(test)
        # handle each of the requirements
        for requirement in requirements:
            if requirement.get('type') in self.supported_requirements:
                requirement_handler = self.supported_requirements.get(
                    requirement.pop('type'))
                requirement_handler(requirement)

    def resolve(self):
        for test in self.references:
            if os.path.isfile(test):
                # it can also be a Python executable representation, but let's
                # assume it is a test for now.
                self._resolve_from_docstring(test)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('reference', nargs='+', help='Test reference')
    args = parser.parse_args()
    resolver = RequirementsResolver(args.reference)
    resolver.resolve()


if __name__ == '__main__':
    main()
