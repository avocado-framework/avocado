import os

from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLICmd
from avocado.core import data_dir, output
from avocado.utils import vmimage, astring


def list_downloaded_images():
    """
    List the available Image inside avocado cache

    :return: list with image's parameters
    :rtype: list of dicts
    """
    images = []
    for cache_dir in data_dir.get_cache_dirs():
        cache_dir = os.path.join(cache_dir, 'vmimage')
        for distro in os.listdir(cache_dir):
            for version in os.listdir(os.path.join(cache_dir, distro)):
                for arch in os.listdir(os.path.join(cache_dir, distro, version)):
                    image_dir = os.path.join(cache_dir, distro, version, arch)
                    file_path = get_image_path(image_dir)
                    if file_path:
                        images.append({"name": distro, "version": version,
                                       "arch": arch, "file": file_path})
    return images


def download_image(distro, version=None, arch=None):
    """
    Downloads the vmimge to the vmimage cache directory if isn't already exists.

    :param distro: Name of image distribution
    :type distro: str
    :param version: Version of image
    :type version: str
    :param arch: Architecture of image
    :type arch: str
    :raise AttributeError: When image can't be downloaded
    :return: Information about downloaded image
    :rtype: dict
    """

    cache_dir = data_dir.get_cache_dirs()[0]
    image_info = vmimage.get_best_provider(name=distro, version=version,
                                           arch=arch,)
    image_dir = os.path.join(cache_dir, 'vmimage', image_info.name,
                             str(image_info.version), image_info.arch)
    file_path = get_image_path(image_dir)
    if not os.path.exists(image_dir) or file_path is None:
        image_info = vmimage.get(name=distro, version=version, arch=arch,
                                 cache_dir=cache_dir)
        file_path = image_info.base_image
    image = {'name': distro, 'version': image_info.version,
             'arch': image_info.arch, 'file': file_path}
    return image


def get_image_path(directory):
    """
    Finds path to the image inside directory.
    :param directory: Directory where should by image
    :return: Path to the image or if image don't exists return None
    :rtype: str
    """
    for root, _, files in os.walk(directory):
        if files:
            files.sort(key=len)
            return os.path.join(root, files[0])
    return None


def display_images_list(images):
    """
    Displays table with information about images

    :param images: list with image's parameters
    :type images: list of dicts
    """
    image_matrix = [[image['name'], image['version'], image['arch'],
                     image['file']] for image in images]
    LOG_UI.debug('\n')
    header = (output.TERM_SUPPORT.header_str('Provider'),
              output.TERM_SUPPORT.header_str('Version'),
              output.TERM_SUPPORT.header_str('Architecture'),
              output.TERM_SUPPORT.header_str('File'))
    for line in astring.iter_tabular_output(image_matrix, header=header,
                                            strip=True):
        LOG_UI.debug(line)
    LOG_UI.debug('\n')


class VMimage(CLICmd):
    """
    Implements the avocado 'vmimage' subcommand
    """

    name = 'vmimage'
    description = 'Provides VM images acquired from official repositories'

    def configure(self, parser):
        parser = super(VMimage, self).configure(parser)
        parser.add_argument('--list',
                            help='List of all downloaded images',
                            action='store_true')
        subparsers = parser.add_subparsers()
        download_subcommand_parser = subparsers.add_parser(
            'get', help="Downloads chosen VMimage if it's not already in the cache")
        download_subcommand_parser.add_argument('--distro',
                                                help='Name of image distribution',
                                                required=True)
        download_subcommand_parser.add_argument('--distro-version',
                                                help='Required version of image')
        download_subcommand_parser.add_argument('--arch',
                                                help='Required architecture image')

    def run(self, config):
        if config['list'] is True:
            images = list_downloaded_images()
            display_images_list(images)
        elif config.get('distro', None):
            image = {'name': config['distro'],
                     'version': config.get('distro_version', None),
                     'arch': config.get('arch', None), 'file': None}
            try:
                image = download_image(config['distro'],
                                       config.get('distro_version', None),
                                       config.get('arch', None))
                LOG_UI.debug("The image was downloaded:")
            except AttributeError:
                LOG_UI.debug("The image couldn't be downloaded:")
            display_images_list([image])
