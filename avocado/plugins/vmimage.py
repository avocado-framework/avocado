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
    cache_dirs = data_dir.get_cache_dirs()
    providers = [provider() for provider in vmimage.list_providers()]

    for cache_dir in cache_dirs:
        for root, _, files in os.walk(cache_dir):
            if files:
                for filename in files:
                    for provider in providers:
                        image = provider.get_image_parameters(filename)
                        if image is not None:
                            image["name"] = provider.name
                            image["file"] = os.path.join(root, filename)
                            images.append(image)
                            break
    return images


def download_image(provider, version=None, arch=None):
    """
    Downloads image to the avocado cache if its not already there

    :param provider: Name of the Image Provider, usually matches the distro name.
    :type provider: str
    :param version: (optional) Version of the system image.
    :type version: str
    :param arch: (optional) Architecture of the system image.
    :type arch: str
    """
    cache_dirs = data_dir.get_cache_dirs()
    image = vmimage.get(name=provider, version=version,
                        arch=arch, cache_dir=cache_dirs)

    LOG_UI.info("The image was downloaded:")
    display_images_list([image])


def display_images_list(images):
    """
    Displays table with information about images

    :param images: list with image's parameters
    :type images: list of dicts
    """
    image_matrix = [[image['name'], image['version'], image['arch'],
                     image['file']] for image in images]
    LOG_UI.info('\n')
    header = (output.TERM_SUPPORT.header_str('Provider'),
              output.TERM_SUPPORT.header_str('Version'),
              output.TERM_SUPPORT.header_str('Architecture'),
              output.TERM_SUPPORT.header_str('File'))
    for line in astring.iter_tabular_output(image_matrix, header=header,
                                            strip=True):
        LOG_UI.info(line)
    LOG_UI.info('\n')


class VMimage(CLICmd):
    """
    Implements the avocado 'vmimage' subcommand
    """

    name = 'vmimage'
    description = 'Provides VM images acquired from official repositories'

    def configure(self, parser):
        parser = super(VMimage, self).configure(parser)
        subparsers = parser.add_subparsers()
        parser.add_argument('--list-downloaded',
                            help='List of all downloaded images',
                            action='store_true')
        download_subcommand_parser = subparsers.add_parser(
            'download', help='Downloads chosen VMimage')
        download_subcommand_parser.add_argument('--provider',
                                                help='Name of image Provider',
                                                required=True)
        download_subcommand_parser.add_argument('--version',
                                                help='Required version of '
                                                     'downloaded image')
        download_subcommand_parser.add_argument('--arch',
                                                help='Required architecture of '
                                                     'downloaded image')

    def run(self, config):
        if config['list_downloaded'] is True:
            images = list_downloaded_images()
            display_images_list(images)
        else:
            download_image(config['provider'], config['version'], config['arch'])
