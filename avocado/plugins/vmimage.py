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
        else:
            # Downloading the image
            cache_dirs = data_dir.get_cache_dirs()
            image = vmimage.get(name=config['distro'],
                                version=config['distro_version'],
                                arch=config['arch'], cache_dir=cache_dirs)

            LOG_UI.info("The image was downloaded:")
            image = [{'name': image.name, 'version': image.version,
                      'arch': image.arch, 'file': image.base_image}]
            display_images_list(image)
