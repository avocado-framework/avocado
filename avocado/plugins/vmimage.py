import json
import os
import re

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
        for root, _, files in os.walk(cache_dir):
            if files:
                metadata_files = [pos_json for pos_json in files
                                  if pos_json.endswith('_metadata.json')]
                files = list(set(files) - set(metadata_files))
                for metadata_file in metadata_files:
                    with open(os.path.join(root, metadata_file), 'r') as data:
                        metadata = json.loads(data.read())
                    if isinstance(metadata, dict):
                        if metadata.get("type", None) == "vmimage":
                            provider = None
                            for p in vmimage.IMAGE_PROVIDERS:
                                if p.name == metadata["name"]:
                                    provider = p(metadata["version"],
                                                 metadata["build"],
                                                 metadata["arch"])
                                    break
                            if provider is not None:
                                for image in files:
                                    if re.match(provider.file_name, image):
                                        data = {"name": provider.name,
                                                "version": provider.version,
                                                "arch": provider.arch,
                                                "file": os.path.join(root, image)}
                                        images.append(data)
                                        break
    return images


def download_image(distro, version=None, arch=None):
    """
    Downloads the vmimage to the cache directory if doesn't already exist

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
    image_info = vmimage.get(name=distro, version=version, arch=arch,
                             cache_dir=cache_dir)
    file_path = image_info.base_image
    image = {'name': distro, 'version': image_info.version,
             'arch': image_info.arch, 'file': file_path}
    return image


def display_images_list(images):
    """
    Displays table with information about images
    :param images: list with image's parameters
    :type images: list of dicts
    """
    image_matrix = [[image['name'], image['version'], image['arch'],
                     image['file']] for image in images]
    header = (output.TERM_SUPPORT.header_str('Provider'),
              output.TERM_SUPPORT.header_str('Version'),
              output.TERM_SUPPORT.header_str('Architecture'),
              output.TERM_SUPPORT.header_str('File'))
    for line in astring.iter_tabular_output(image_matrix, header=header,
                                            strip=True):
        LOG_UI.debug(line)


class VMimage(CLICmd):
    """
    Implements the avocado 'vmimage' subcommand
    """

    name = 'vmimage'
    description = 'Provides VM images acquired from official repositories'

    def configure(self, parser):
        parser = super(VMimage, self).configure(parser)
        subcommands = parser.add_subparsers(dest='vmimage_subcommand')
        subcommands.required = True
        subcommands.add_parser('list', help='List of all downloaded images')
        download_subcommand_parser = subcommands.add_parser(
            'get', help="Downloads chosen VMimage if it's not already in the cache")
        download_subcommand_parser.add_argument('--distro',
                                                help='Name of image distribution',
                                                required=True)
        download_subcommand_parser.add_argument('--distro-version',
                                                help='Required version of image')
        download_subcommand_parser.add_argument('--arch',
                                                help='Required architecture image')

    def run(self, config):
        subcommand = config.get("vmimage_subcommand")
        if subcommand == 'list':
            images = list_downloaded_images()
            display_images_list(images)
        elif subcommand == 'get':
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
