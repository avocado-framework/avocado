import urllib2
import logging
import os
import glob
from autotest.client import utils, test_config
from autotest.client.shared import git, error
import data_dir
import re


def get_known_backends():
    """
    Return virtualization backends supported by virt-test.
    """
    # Generic means the test can run in multiple backends, such as libvirt
    # and qemu.
    known_backends = ['generic']
    known_backends += os.listdir(data_dir.BASE_BACKEND_DIR)
    return known_backends


def get_test_provider_names(backend=None):
    """
    Get the names of all test providers available in test-providers.d.

    :return: List with the names of all test providers.
    """
    provider_name_list = []
    provider_dir = data_dir.get_test_providers_dir()
    for provider in glob.glob(os.path.join(provider_dir, '*.ini')):
        provider_name = os.path.basename(provider).split('.')[0]
        provider_info = get_test_provider_info(provider_name)
        if backend is not None:
            if backend in provider_info['backends']:
                provider_name_list.append(provider_name)
        else:
            provider_name_list.append(provider_name)
    return provider_name_list


def get_test_provider_subdirs(backend=None):
    """
    Get information of all test provider subdirs for a given backend.

    If no backend is provided, return all subdirs with tests.

    :param backend: Backend type, such as 'qemu'.
    :return: List of directories that contain tests for the given backend.
    """
    subdir_list = []
    for provider_name in get_test_provider_names():
        provider_info = get_test_provider_info(provider_name)
        backends_info = provider_info['backends']
        if backend is not None:
            if backend in backends_info:
                subdir_list.append(backends_info[backend]['path'])
        else:
            for b in backends_info:
                subdir_list.append(backends_info[b]['path'])
    return subdir_list


def get_test_provider_info(provider):
    """
    Get a dictionary with relevant test provider info, such as:

    * provider uri (git repo or filesystem location)
    * provider git repo data, such as branch, ref, pubkey
    * backends that this provider has tests for. For each backend type the
        provider has tests for, the 'path' will be also available.

    :param provider: Test provider name, such as 'io-github-autotest-qemu'.
    """
    provider_info = {}
    provider_path = os.path.join(data_dir.get_test_providers_dir(),
                                 '%s.ini' % provider)
    provider_cfg = test_config.config_loader(provider_path)
    provider_info['name'] = provider
    provider_info['uri'] = provider_cfg.get('provider', 'uri')
    provider_info['branch'] = provider_cfg.get('provider', 'branch', 'master')
    provider_info['ref'] = provider_cfg.get('provider', 'ref')
    provider_info['pubkey'] = provider_cfg.get('provider', 'pubkey')
    provider_info['backends'] = {}

    for backend in get_known_backends():
        subdir = provider_cfg.get(backend, 'subdir')
        if subdir is not None:
            if provider_info['uri'].startswith('file://'):
                src = os.path.join(provider_info['uri'][7:],
                                   subdir)
            else:
                src = os.path.join(data_dir.get_test_provider_dir(provider),
                                   subdir)
            provider_info['backends'].update({backend: {'path': src}})

    return provider_info


def download_test_provider(provider, update=False):
    """
    Download a test provider defined on a .ini file inside test-providers.d.

    This function will only download test providers that are in git repos.
    Local filesystems don't need this functionality.

    :param provider: Test provider name, such as 'io-github-autotest-qemu'.
    """
    provider_info = get_test_provider_info(provider)
    uri = provider_info.get('uri')
    if not uri.startswith('file://'):
        uri = provider_info.get('uri')
        branch = provider_info.get('branch')
        ref = provider_info.get('ref')
        pubkey = provider_info.get('pubkey')
        download_dst = data_dir.get_test_provider_dir(provider)
        repo_downloaded = os.path.isdir(os.path.join(download_dst, '.git'))
        original_dir = os.getcwd()
        if not repo_downloaded or update:
            download_dst = git.get_repo(uri=uri, branch=branch, commit=ref,
                                        destination_dir=download_dst)
            os.chdir(download_dst)
            try:
                utils.run('git remote add origin %s' % uri)
            except error.CmdError:
                pass
            utils.run('git pull origin %s' % branch)
        os.chdir(download_dst)
        utils.system('git log -1')
        os.chdir(original_dir)


def download_all_test_providers(update=False):
    """
    Download all available test providers.
    """
    for provider in get_test_provider_names():
        download_test_provider(provider, update)


def get_all_assets():
    asset_data_list = []
    download_dir = data_dir.get_download_dir()
    for asset in glob.glob(os.path.join(download_dir, '*.ini')):
        asset_name = os.path.basename(asset).split('.')[0]
        asset_data_list.append(get_asset_info(asset_name))
    return asset_data_list


def get_file_asset(title, src_path, destination):
    if not os.path.isabs(destination):
        destination = os.path.join(data_dir.get_data_dir(), destination)

    for ext in (".xz", ".gz", ".7z", ".bz2"):
        if os.path.exists(src_path + ext):
            destination = destination + ext
            logging.debug('Found source image %s', destination)
            return {
                'url': None, 'sha1_url': None, 'destination': src_path + ext,
                'destination_uncompressed': destination,
                'uncompress_cmd': None, 'shortname': title, 'title': title,
                'downloaded': True}

    if os.path.exists(src_path):
        logging.debug('Found source image %s', destination)
        return {'url': src_path, 'sha1_url': None, 'destination': destination,
                'destination_uncompressed': None, 'uncompress_cmd': None,
                'shortname': title, 'title': title,
                'downloaded': os.path.exists(destination)}

    return None


def get_asset_info(asset):
    asset_info = {}
    asset_path = os.path.join(data_dir.get_download_dir(), '%s.ini' % asset)
    asset_cfg = test_config.config_loader(asset_path)

    asset_info['url'] = asset_cfg.get(asset, 'url')
    asset_info['sha1_url'] = asset_cfg.get(asset, 'sha1_url')
    asset_info['title'] = asset_cfg.get(asset, 'title')
    destination = asset_cfg.get(asset, 'destination')
    if not os.path.isabs(destination):
        destination = os.path.join(data_dir.get_data_dir(), destination)
    asset_info['destination'] = destination
    asset_info['asset_exists'] = os.path.isfile(destination)

    # Optional fields
    d_uncompressed = asset_cfg.get(asset, 'destination_uncompressed')
    if d_uncompressed is not None and not os.path.isabs(d_uncompressed):
        d_uncompressed = os.path.join(data_dir.get_data_dir(),
                                      d_uncompressed)
    asset_info['destination_uncompressed'] = d_uncompressed
    asset_info['uncompress_cmd'] = asset_cfg.get(asset, 'uncompress_cmd')

    return asset_info


def uncompress_asset(asset_info, force=False):
    destination = asset_info['destination']
    uncompress_cmd = asset_info['uncompress_cmd']
    destination_uncompressed = asset_info['destination_uncompressed']

    archive_re = re.compile(r".*\.(gz|xz|7z|bz2)$")
    if destination_uncompressed is not None:
        if uncompress_cmd is None:
            match = archive_re.match(destination)
            if match:
                if match.group(1) == 'gz':
                    uncompress_cmd = ('gzip -cd %s > %s' %
                                      (destination, destination_uncompressed))
                elif match.group(1) == 'xz':
                    uncompress_cmd = ('xz -cd %s > %s' %
                                      (destination, destination_uncompressed))
                elif match.group(1) == 'bz2':
                    uncompress_cmd = ('bzip2 -cd %s > %s' %
                                      (destination, destination_uncompressed))
                elif match.group(1) == '7z':
                    uncompress_cmd = '7za -y e %s' % destination
        else:
            uncompress_cmd = "%s %s" % (uncompress_cmd, destination)

    if uncompress_cmd is not None:
        uncompressed_file_exists = os.path.exists(destination_uncompressed)
        force = (force or not uncompressed_file_exists)

        if os.path.isfile(destination) and force:
            os.chdir(os.path.dirname(destination_uncompressed))
            utils.run(uncompress_cmd)


def download_file(asset_info, interactive=False, force=False):
    """
    Verifies if file that can be find on url is on destination with right hash.

    This function will verify the SHA1 hash of the file. If the file
    appears to be missing or corrupted, let the user know.

    :param asset_info: Dictionary returned by get_asset_info
    """
    file_ok = False
    problems_ignored = False
    had_to_download = False
    sha1 = None

    url = asset_info['url']
    sha1_url = asset_info['sha1_url']
    destination = asset_info['destination']
    title = asset_info['title']

    if sha1_url is not None:
        try:
            logging.info("Verifying expected SHA1 sum from %s", sha1_url)
            sha1_file = urllib2.urlopen(sha1_url)
            sha1_contents = sha1_file.read()
            sha1 = sha1_contents.split(" ")[0]
            logging.info("Expected SHA1 sum: %s", sha1)
        except Exception, e:
            logging.error("Failed to get SHA1 from file: %s", e)
    else:
        sha1 = None

    destination_dir = os.path.dirname(destination)
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)

    if not os.path.isfile(destination):
        logging.warning("File %s not found", destination)
        if interactive:
            answer = utils.ask("Would you like to download it from %s?" % url)
        else:
            answer = 'y'
        if answer == 'y':
            utils.interactive_download(
                url, destination, "Downloading %s" % title)
            had_to_download = True
        else:
            logging.warning("Missing file %s", destination)
    else:
        logging.info("Found %s", destination)
        if sha1 is None:
            answer = 'n'
        else:
            answer = 'y'

        if answer == 'y':
            actual_sha1 = utils.hash_file(destination, method='sha1')
            if actual_sha1 != sha1:
                logging.info("Actual SHA1 sum: %s", actual_sha1)
                if interactive:
                    answer = utils.ask("The file seems corrupted or outdated. "
                                       "Would you like to download it?")
                else:
                    logging.info("The file seems corrupted or outdated")
                    answer = 'y'
                if answer == 'y':
                    logging.info("Updating image to the latest available...")
                    while not file_ok:
                        utils.interactive_download(url, destination, title)
                        sha1_post_download = utils.hash_file(destination,
                                                             method='sha1')
                        had_to_download = True
                        if sha1_post_download != sha1:
                            logging.error("Actual SHA1 sum: %s", actual_sha1)
                            if interactive:
                                answer = utils.ask("The file downloaded %s is "
                                                   "corrupted. Would you like "
                                                   "to try again?" %
                                                   destination)
                            else:
                                answer = 'n'
                            if answer == 'n':
                                problems_ignored = True
                                logging.error("File %s is corrupted" %
                                              destination)
                                file_ok = True
                            else:
                                file_ok = False
                        else:
                            file_ok = True
            else:
                file_ok = True
                logging.info("SHA1 sum check OK")
        else:
            problems_ignored = True
            logging.info("File %s present, but did not verify integrity",
                         destination)

    if file_ok:
        if not problems_ignored:
            logging.info("%s present, with proper checksum", destination)

    uncompress_asset(asset_info=asset_info, force=force or had_to_download)


def download_asset(asset, interactive=True, restore_image=False):
    """
    Download an asset defined on an asset file.

    Asset files are located under /shared/downloads, are .ini files with the
    following keys defined:

    title
        Title string to display in the download progress bar.
    url
        URL of the resource
    sha1_url
        URL with SHA1 information for the resource, in the form
        sha1sum file_basename
    destination
        Location of your file relative to the data directory
        (TEST_SUITE_ROOT/shared/data)
    destination
        Location of the uncompressed file relative to the data
        directory (TEST_SUITE_ROOT/shared/data)
    uncompress_cmd
        Command that needs to be executed with the compressed
        file as a parameter

    :param asset: String describing an asset file.
    :param interactive: Whether to ask the user before downloading the file.
    :param restore_image: If the asset is a compressed image, we can uncompress
                          in order to restore the image.
    """
    asset_info = get_asset_info(asset)
    destination = asset_info['destination']

    if (interactive and not os.path.isfile(destination)):
        answer = utils.ask("File %s not present. Do you want to download it?" %
                           asset_info['title'])
    else:
        answer = "y"

    if answer == "y":
        download_file(asset_info=asset_info, interactive=interactive,
                      force=restore_image)
