import logging
import os
import glob
import shutil
from autotest.client.shared import logging_manager, error
from autotest.client import utils
import utils_misc
import data_dir
import asset
import cartesian_config
import utils_selinux
import defaults

basic_program_requirements = ['7za', 'tcpdump', 'nc', 'ip', 'arping']

recommended_programs = {'qemu': [('qemu-kvm', 'kvm'), ('qemu-img',),
                                 ('qemu-io',)],
                        'libvirt': [('virsh',), ('virt-install',),
                                    ('fakeroot',), ('semanage',),
                                    ('getfattr',), ('restorecon',)],
                        'openvswitch': [],
                        'lvsb': [('semanage',), ('getfattr',), ('restorecon',)],
                        'v2v': [],
                        'libguestfs': [('perl',)]}

mandatory_programs = {'qemu': basic_program_requirements + ['gcc'],
                      'libvirt': basic_program_requirements,
                      'openvswitch': basic_program_requirements,
                      'lvsb': ['virt-sandbox', 'virt-sandbox-service', 'virsh'],
                      'v2v': basic_program_requirements,
                      'libguestfs': basic_program_requirements}

mandatory_headers = {'qemu': ['Python.h', 'types.h', 'socket.h', 'unistd.h'],
                     'libvirt': [],
                     'openvswitch': [],
                     'v2v': [],
                     'lvsb': [],
                     'libguestfs': []}

first_subtest = {'qemu': ['unattended_install', 'steps'],
                 'libvirt': ['unattended_install'],
                 'openvswitch': ['unattended_install'],
                 'v2v': ['unattended_install'],
                 'libguestfs': ['unattended_install'],
                 'lvsb': []}

last_subtest = {'qemu': ['shutdown'],
                'libvirt': ['shutdown', 'remove_guest'],
                'openvswitch': ['shutdown'],
                'v2v': ['shutdown'],
                'libguestfs': ['shutdown'],
                'lvsb': []}

test_filter = ['__init__', 'cfg', 'dropin.py']


def get_guest_os_info_list(test_name, guest_os):
    """
    Returns a list of matching assets compatible with the specified test name
    and guest OS
    """
    os_info_list = []

    cartesian_parser = cartesian_config.Parser()
    cartesian_parser.parse_file(data_dir.get_backend_cfg_path(test_name, 'guest-os.cfg'))
    cartesian_parser.only_filter(guest_os)
    dicts = cartesian_parser.get_dicts()

    for params in dicts:
        image_name = params.get('image_name', 'image').split('/')[-1]
        shortname = params.get('shortname', guest_os)
        os_info_list.append({'asset': image_name, 'variant': shortname})

    if not os_info_list:
        logging.error("Could not find any assets compatible with %s for %s",
                      guest_os, test_name)
        raise ValueError("Missing compatible assets for %s", guest_os)

    return os_info_list


def _get_config_filter():
    config_filter = ['__init__', ]
    for provider_subdir in asset.get_test_provider_subdirs():
        config_filter.append(os.path.join('%s' % provider_subdir, 'cfg'))
    return config_filter

config_filter = _get_config_filter()


def verify_recommended_programs(t_type):
    cmds = recommended_programs[t_type]
    for cmd_aliases in cmds:
        for cmd in cmd_aliases:
            found = None
            try:
                found = utils_misc.find_command(cmd)
                logging.info(found)
                break
            except ValueError:
                pass
        if found is None:
            if len(cmd_aliases) == 1:
                logging.info("Recommended command %s missing. You may "
                             "want to install it if not building from "
                             "source.", cmd_aliases[0])
            else:
                logging.info("Recommended command missing. You may "
                             "want to install it if not building it from "
                             "source. Aliases searched: %s", cmd_aliases)


def verify_mandatory_programs(t_type):
    failed_cmds = []
    cmds = mandatory_programs[t_type]
    for cmd in cmds:
        try:
            logging.info(utils_misc.find_command(cmd))
        except ValueError:
            logging.error("Required command %s is missing. You must "
                          "install it", cmd)
            failed_cmds.append(cmd)

    includes = mandatory_headers[t_type]
    available_includes = glob.glob('/usr/include/*/*')
    for include in available_includes:
        include_basename = os.path.basename(include)
        if include_basename in includes:
            logging.info(include)
            includes.pop(includes.index(include_basename))

    if includes:
        for include in includes:
            logging.error("Required include %s is missing. You may have to "
                          "install it", include)

    failures = failed_cmds + includes

    if failures:
        raise ValueError('Missing (cmds/includes): %s' % " ".join(failures))


def write_subtests_files(config_file_list, output_file_object, test_type=None):
    '''
    Writes a collection of individual subtests config file to one output file

    Optionally, for tests that we know their type, write the 'virt_test_type'
    configuration automatically.
    '''
    if test_type is not None:
        output_file_object.write("    - @type_specific:\n")
        output_file_object.write("        variants subtest:\n")

    for provider_name, config_path in config_file_list:
        config_file = open(config_path, 'r')

        write_test_type_line = False
        write_provider_line = False

        for line in config_file.readlines():
            if line.startswith('- ') and provider_name is not None:
                name, deps = line.split(":")
                name = name.split('-')[-1].strip()
                if name[0] == "@":
                    name = name[1:]
                line = "- %s.%s:%s" % (provider_name, name, deps)

            # special virt_test_type line output
            if test_type is not None:
                if write_test_type_line:
                    type_line = ("                virt_test_type = %s\n" %
                                 test_type)
                    output_file_object.write(type_line)
                    provider_line = ("                provider = %s\n" %
                                     provider_name)
                    output_file_object.write(provider_line)
                    write_test_type_line = False
                elif line.startswith('- '):
                    write_test_type_line = True
                output_file_object.write("            %s" % line)
            else:
                if write_provider_line:
                    provider_line = ("        provider = %s\n" %
                                     provider_name)
                    output_file_object.write(provider_line)
                    write_provider_line = False
                elif line.startswith('- '):
                    write_provider_line = True
                # regular line output
                output_file_object.write("    %s" % line)

        config_file.close()


def get_directory_structure(rootdir, guest_file):
    rootdir = rootdir.rstrip(os.sep)
    start = rootdir.rfind(os.sep) + 1
    previous_indent = 0
    indent = 0
    number_variants = 0
    for path, subdirs, files in os.walk(rootdir):
        folders = path[start:].split(os.sep)
        folders = folders[1:]
        indent = len(folders)
        if indent > previous_indent:
            guest_file.write("%svariants:\n" %
                             (4 * (indent + number_variants - 1) * " "))
            number_variants += 1
        elif indent < previous_indent:
            number_variants = indent
        indent += number_variants
        try:
            base_folder = folders[-1]
        except IndexError:
            base_folder = []
        base_cfg = "%s.cfg" % base_folder
        base_cfg_path = os.path.join(os.path.dirname(path), base_cfg)
        if os.path.isfile(base_cfg_path):
            base_file = open(base_cfg_path, 'r')
            for line in base_file.readlines():
                guest_file.write("%s%s" % ((4 * (indent - 1) * " "), line))
        else:
            if base_folder:
                guest_file.write("%s- %s:\n" %
                                 ((4 * (indent - 1) * " "), base_folder))
        variant_printed = False
        if files:
            files.sort()
            for f in files:
                if f.endswith(".cfg"):
                    bf = f[:len(f) - 4]
                    if bf not in subdirs:
                        if not variant_printed:
                            guest_file.write("%svariants:\n" %
                                             ((4 * (indent) * " ")))
                            variant_printed = True
                        base_file = open(os.path.join(path, f), 'r')
                        for line in base_file.readlines():
                            guest_file.write("%s%s" %
                                             ((4 * (indent + 1) * " "), line))
        indent -= number_variants
        previous_indent = indent


def create_guest_os_cfg(t_type):
    root_dir = data_dir.get_root_dir()
    guest_os_cfg_dir = os.path.join(root_dir, 'shared', 'cfg', 'guest-os')
    guest_os_cfg_path = data_dir.get_backend_cfg_path(t_type, 'guest-os.cfg')
    guest_os_cfg_file = open(guest_os_cfg_path, 'w')
    get_directory_structure(guest_os_cfg_dir, guest_os_cfg_file)


def create_subtests_cfg(t_type):
    root_dir = data_dir.get_root_dir()

    specific_test_list = []
    specific_file_list = []
    specific_subdirs = asset.get_test_provider_subdirs(t_type)
    provider_names_specific = asset.get_test_provider_names(t_type)

    provider_info_specific = []
    for specific_provider in provider_names_specific:
        provider_info_specific.append(asset.get_test_provider_info(specific_provider))

    for subdir in specific_subdirs:
        specific_test_list += data_dir.SubdirGlobList(subdir,
                                                      '*.py',
                                                      test_filter)
        specific_file_list += data_dir.SubdirGlobList(subdir,
                                                      '*.cfg',
                                                      config_filter)

    shared_test_list = []
    shared_file_list = []
    shared_subdirs = asset.get_test_provider_subdirs('generic')
    provider_names_shared = asset.get_test_provider_names('generic')

    provider_info_shared = []
    for shared_provider in provider_names_shared:
        provider_info_shared.append(asset.get_test_provider_info(shared_provider))

    if not t_type == 'lvsb':
        for subdir in shared_subdirs:
            shared_test_list += data_dir.SubdirGlobList(subdir,
                                                        '*.py',
                                                        test_filter)
            shared_file_list += data_dir.SubdirGlobList(subdir,
                                                        '*.cfg',
                                                        config_filter)

    all_specific_test_list = []
    for test in specific_test_list:
        for p in provider_info_specific:
            provider_base_path = p['backends'][t_type]['path']
            if provider_base_path in test:
                provider_name = p['name']
                break

        basename = os.path.basename(test)
        if basename != "__init__.py":
            all_specific_test_list.append("%s.%s" %
                                          (provider_name,
                                           basename.split(".")[0]))
    all_shared_test_list = []
    for test in shared_test_list:
        for p in provider_info_shared:
            provider_base_path = p['backends']['generic']['path']
            if provider_base_path in test:
                provider_name = p['name']
                break

        basename = os.path.basename(test)
        if basename != "__init__.py":
            all_shared_test_list.append("%s.%s" %
                                        (provider_name,
                                         basename.split(".")[0]))

    all_specific_test_list.sort()
    all_shared_test_list.sort()
    all_test_list = set(all_specific_test_list + all_shared_test_list)

    first_subtest_file = []
    last_subtest_file = []
    non_dropin_tests = []
    tmp = []

    for shared_file in shared_file_list:
        provider_name = None
        for p in provider_info_shared:
            provider_base_path = p['backends']['generic']['path']
            if provider_base_path in shared_file:
                provider_name = p['name']
                break

        shared_file_obj = open(shared_file, 'r')
        for line in shared_file_obj.readlines():
            line = line.strip()
            if line.startswith("type"):
                cartesian_parser = cartesian_config.Parser()
                cartesian_parser.parse_string(line)
                td = cartesian_parser.get_dicts().next()
                values = td['type'].split(" ")
                for value in values:
                    if t_type not in non_dropin_tests:
                        non_dropin_tests.append("%s.%s" %
                                                (provider_name, value))

        shared_file_name = os.path.basename(shared_file)
        shared_file_name = shared_file_name.split(".")[0]
        if shared_file_name in first_subtest[t_type]:
            if [provider_name, shared_file] not in first_subtest_file:
                first_subtest_file.append([provider_name, shared_file])
        elif shared_file_name in last_subtest[t_type]:
            if [provider_name, shared_file] not in last_subtest_file:
                last_subtest_file.append([provider_name, shared_file])
        else:
            if [provider_name, shared_file] not in tmp:
                tmp.append([provider_name, shared_file])
    shared_file_list = tmp

    tmp = []
    for shared_file in specific_file_list:
        provider_name = None
        for p in provider_info_specific:
            provider_base_path = p['backends'][t_type]['path']
            if provider_base_path in shared_file:
                provider_name = p['name']
                break

        shared_file_obj = open(shared_file, 'r')
        for line in shared_file_obj.readlines():
            line = line.strip()
            if line.startswith("type"):
                cartesian_parser = cartesian_config.Parser()
                cartesian_parser.parse_string(line)
                td = cartesian_parser.get_dicts().next()
                values = td['type'].split(" ")
                for value in values:
                    if value not in non_dropin_tests:
                        non_dropin_tests.append("%s.%s" %
                                                (provider_name, value))

        shared_file_name = os.path.basename(shared_file)
        shared_file_name = shared_file_name.split(".")[0]
        if shared_file_name in first_subtest[t_type]:
            if [provider_name, shared_file] not in first_subtest_file:
                first_subtest_file.append([provider_name, shared_file])
        elif shared_file_name in last_subtest[t_type]:
            if [provider_name, shared_file] not in last_subtest_file:
                last_subtest_file.append([provider_name, shared_file])
        else:
            if [provider_name, shared_file] not in tmp:
                tmp.append([provider_name, shared_file])
    specific_file_list = tmp

    non_dropin_tests.sort()
    non_dropin_tests = set(non_dropin_tests)
    dropin_tests = all_test_list - non_dropin_tests
    dropin_file_list = []
    tmp_dir = data_dir.get_tmp_dir()
    if not os.path.isdir(tmp_dir):
        os.makedirs(tmp_dir)

    for dropin_test in dropin_tests:
        provider = dropin_test.split(".")[0]
        d_type = dropin_test.split(".")[-1]
        autogen_cfg_path = os.path.join(tmp_dir,
                                        '%s.cfg' % dropin_test)
        autogen_cfg_file = open(autogen_cfg_path, 'w')
        autogen_cfg_file.write("# Drop-in test - auto generated snippet\n")
        autogen_cfg_file.write("- %s:\n" % dropin_test)
        autogen_cfg_file.write("    virt_test_type = %s\n" % t_type)
        autogen_cfg_file.write("    type = %s\n" % d_type)
        autogen_cfg_file.close()
        dropin_file_list.append([provider, autogen_cfg_path])

    dropin_file_list_2 = []
    dropin_tests = os.listdir(os.path.join(data_dir.get_root_dir(), "dropin"))
    dropin_cfg_path = os.path.join(tmp_dir, 'dropin.cfg')
    dropin_cfg_file = open(dropin_cfg_path, 'w')
    dropin_cfg_file.write("# Auto generated snippet for dropin tests\n")
    dropin_cfg_file.write("- dropin:\n")
    dropin_cfg_file.write("    variants:\n")
    for dropin_test in dropin_tests:
        if dropin_test == "README":
            continue
        dropin_cfg_file.write("        - %s:\n" % dropin_test)
        dropin_cfg_file.write("            virt_test_type = %s\n" % t_type)
        dropin_cfg_file.write("            type = dropin\n")
        dropin_cfg_file.write("            start_vm = no\n")
        dropin_cfg_file.write("            dropin_path = %s\n" % dropin_test)
    dropin_cfg_file.close()
    dropin_file_list_2.append(['io-github-autotest-qemu', dropin_cfg_path])

    subtests_cfg = os.path.join(root_dir, 'backends', t_type, 'cfg',
                                'subtests.cfg')
    subtests_file = open(subtests_cfg, 'w')
    subtests_file.write(
        "# Do not edit, auto generated file from subtests config\n")

    subtests_file.write("variants subtest:\n")
    write_subtests_files(first_subtest_file, subtests_file)
    write_subtests_files(specific_file_list, subtests_file, t_type)
    write_subtests_files(shared_file_list, subtests_file)
    write_subtests_files(dropin_file_list, subtests_file)
    write_subtests_files(dropin_file_list_2, subtests_file)
    write_subtests_files(last_subtest_file, subtests_file)

    subtests_file.close()


def create_config_files(test_dir, shared_dir, interactive, step=None,
                        force_update=False):
    def is_file_tracked(fl):
        tracked_result = utils.run("git ls-files %s --error-unmatch" % fl,
                                   ignore_status=True, verbose=False)
        return (tracked_result.exit_status == 0)

    if step is None:
        step = 0
    logging.info("")
    step += 1
    logging.info("%d - Generating config set", step)
    config_file_list = data_dir.SubdirGlobList(os.path.join(test_dir, "cfg"),
                                               "*.cfg",
                                               config_filter)
    config_file_list = [cf for cf in config_file_list if is_file_tracked(cf)]
    config_file_list_shared = glob.glob(os.path.join(shared_dir, "cfg",
                                                     "*.cfg"))

    # Handle overrides of cfg files. Let's say a test provides its own
    # subtest.cfg.sample, this file takes precedence over the shared
    # subtest.cfg.sample. So, yank this file from the cfg file list.

    config_file_list_shared_keep = []
    for cf in config_file_list_shared:
        basename = os.path.basename(cf)
        target = os.path.join(test_dir, "cfg", basename)
        if target not in config_file_list:
            config_file_list_shared_keep.append(cf)

    config_file_list += config_file_list_shared_keep
    for config_file in config_file_list:
        src_file = config_file
        dst_file = os.path.join(test_dir, "cfg", os.path.basename(config_file))
        if not os.path.isfile(dst_file):
            logging.debug("Creating config file %s from sample", dst_file)
            shutil.copyfile(src_file, dst_file)
        else:
            diff_cmd = "diff -Naur %s %s" % (dst_file, src_file)
            diff_result = utils.run(
                diff_cmd, ignore_status=True, verbose=False)
            if diff_result.exit_status != 0:
                logging.info("%s result:\n %s",
                             diff_result.command, diff_result.stdout)
                if interactive:
                    answer = utils.ask("Config file  %s differs from %s."
                                       "Overwrite?" % (dst_file, src_file))
                elif force_update:
                    answer = "y"
                else:
                    answer = "n"

                if answer == "y":
                    logging.debug("Restoring config file %s from sample",
                                  dst_file)
                    shutil.copyfile(src_file, dst_file)
                else:
                    logging.debug("Preserving existing %s file", dst_file)
            else:
                logging.debug("Config file %s exists, not touching", dst_file)


def haz_defcon(datadir, imagesdir, isosdir, tmpdir):
    """
    Compare current types from Defaults, or if default, compare on-disk type
    """
    # Searching through default contexts is very slow.
    # Exploit restorecon -n to find any defaults
    try:
        # First element is list, third tuple item is desired context
        data_type = utils_selinux.diff_defcon(datadir, False)[0][2]
    except IndexError:  # object matches default, get current on-disk context
        data_type = utils_selinux.get_context_of_file(datadir)
    # Extract just the type component
    data_type = utils_selinux.get_type_from_context(data_type)

    try:
        # Do not descend, we want to know the base-dir def. context
        images_type = utils_selinux.diff_defcon(imagesdir, False)[0][2]
    except IndexError:
        images_type = utils_selinux.get_context_of_file(imagesdir)
    images_type = utils_selinux.get_type_from_context(images_type)

    try:
        isos_type = utils_selinux.diff_defcon(isosdir, False)[0][2]
    except IndexError:
        isos_type = utils_selinux.get_context_of_file(isosdir)
    isos_type = utils_selinux.get_type_from_context(isos_type)

    try:
        tmp_type = utils_selinux.diff_defcon(tmpdir, False)[0][2]
    except IndexError:
        tmp_type = utils_selinux.get_context_of_file(tmpdir)
    tmp_type = utils_selinux.get_type_from_context(tmp_type)

    # hard-coded values b/c only four of them and widly-used
    if data_type == 'virt_var_lib_t':
        if images_type == 'virt_image_t':
            if isos_type == 'virt_content_t':
                if tmp_type == 'user_tmp_t':
                    return True  # No changes needed
    return False


def set_defcon(datadir, imagesdir, isosdir, tmpdir):
    """
    Tries to set datadir default contexts returns True if changed
    """
    made_changes = False
    try:
        # Returns list of tuple(pathname, from, to) of context differences
        # between on-disk and defaults.  Only interested in top-level
        # object [0] and the context it would change to [2]
        data_type = utils_selinux.diff_defcon(datadir, False)[0][2]
        # Extrach only the type
        existing_data = utils_selinux.get_type_from_context(data_type)
    except IndexError:
        existing_data = None
    try:
        images_type = utils_selinux.diff_defcon(imagesdir, False)[0][2]
        existing_images = utils_selinux.get_type_from_context(images_type)
    except IndexError:
        existing_images = None
    try:
        isos_type = utils_selinux.diff_defcon(isosdir, False)[0][2]
        existing_isos = utils_selinux.get_type_from_context(isos_type)
    except IndexError:
        existing_isos = None

    try:
        tmp_type = utils_selinux.diff_defcon(tmpdir, False)[0][2]
        existing_tmp = utils_selinux.get_type_from_context(tmp_type)
    except IndexError:
        existing_tmp = None

    # Only print slow info message one time
    could_be_slow = False
    msg = "Defining default contexts, this could take a few seconds..."
    # Changing default contexts is *slow*, avoid it if not necessary
    if existing_data is None or existing_data is not 'virt_var_lib_t':
        # semanage gives errors if don't treat /usr & /usr/local the same
        data_regex = utils_selinux.transmogrify_usr_local(datadir)
        logging.info(msg)
        could_be_slow = True
        # This applies only to datadir symlink, not sub-directories!
        utils_selinux.set_defcon('virt_var_lib_t', data_regex)
        made_changes = True

    if existing_images is None or existing_images is not 'virt_image_t':
        # Applies to imagesdir and everything below
        images_regex = utils_selinux.transmogrify_usr_local(imagesdir)
        images_regex = utils_selinux.transmogrify_sub_dirs(images_regex)
        if not could_be_slow:
            logging.info(msg)
            could_be_slow = True
        utils_selinux.set_defcon('virt_image_t', images_regex)
        made_changes = True

    if existing_isos is None or existing_isos is not 'virt_content_t':
        # Applies to isosdir and everything below
        isos_regex = utils_selinux.transmogrify_usr_local(isosdir)
        isos_regex = utils_selinux.transmogrify_sub_dirs(isos_regex)
        if not could_be_slow:
            logging.info(msg)
            could_be_slow = True
        utils_selinux.set_defcon('virt_content_t', isos_regex)
        made_changes = True

    if existing_tmp is None or existing_tmp is not 'user_tmp_t':
        tmp_regex = utils_selinux.transmogrify_usr_local(tmpdir)
        tmp_regex = utils_selinux.transmogrify_sub_dirs(tmp_regex)
        if not could_be_slow:
            logging.info(msg)
            could_be_slow = True
        utils_selinux.set_defcon('user_tmp_t', tmp_regex)
        made_changes = True

    return made_changes


def verify_selinux(datadir, imagesdir, isosdir, tmpdir,
                   interactive, selinux=False):
    """
    Verify/Set/Warn about SELinux and default file contexts for testing.

    :param datadir: Abs. path to data-directory symlink
    :param imagesdir: Abs. path to data/images directory
    :param isosdir: Abs. path to data/isos directory
    :param tmpdir: Abs. path to virt-test tmp dir
    :param interactive: True if running from console
    :param selinux: Whether setup SELinux contexts for shared/data
    """
    # datadir can be a symlink, but these must not have any
    imagesdir = os.path.realpath(imagesdir)
    isosdir = os.path.realpath(isosdir)
    tmpdir = os.path.realpath(tmpdir)
    needs_relabel = None
    try:
        # Raise SeCmdError if selinux not installed
        if utils_selinux.get_status() == 'enforcing':
            # Check if default contexts are set
            if not haz_defcon(datadir, imagesdir, isosdir, tmpdir):
                if selinux:
                    answer = "y"
                else:
                    if interactive:
                        answer = utils.ask("Setup all undefined default SE"
                                           "Linux contexts for shared/data/?")
                    else:
                        answer = "n"
            else:
                answer = "n"
            if answer.lower() == "y":
                # Assume relabeling is needed if changes made
                needs_relabel = set_defcon(datadir, imagesdir, isosdir, tmpdir)
            # Only relabel if files/dirs don't match default
            labels_ok = utils_selinux.verify_defcon(datadir, False)
            labels_ok &= utils_selinux.verify_defcon(imagesdir, True)
            labels_ok &= utils_selinux.verify_defcon(isosdir, True)
            labels_ok &= utils_selinux.verify_defcon(tmpdir, True)
            if labels_ok:
                needs_relabel = False
            else:
                logging.warning("On-disk SELinux labels do not match defaults")
                needs_relabel = True
        # Disabled or Permissive mode is same result as not installed
        else:
            logging.info("SELinux in permissive or disabled, testing"
                         "in enforcing mode is highly encourraged.")
    except utils_selinux.SemanageError:
        logging.info("Could not set default SELinux contexts. Please")
        logging.info("consider installing the semanage program then ")
        logging.info("verifying and/or running running:")
        # Paths must be transmogrified (changed) into regular expressions
        logging.info("semanage fcontext --add -t virt_var_lib_t '%s'",
                     utils_selinux.transmogrify_usr_local(datadir))
        logging.info("semanage fcontext --add -t virt_image_t '%s'",
                     utils_selinux.transmogrify_usr_local(
                         utils_selinux.transmogrify_sub_dirs(imagesdir)))
        logging.info("semanage fcontext --add -t virt_content_t '%s'",
                     utils_selinux.transmogrify_usr_local(
                         utils_selinux.transmogrify_sub_dirs(isosdir)))
        logging.info("semanage fcontext --add -t user_tmp_t '%s'",
                     utils_selinux.transmogrify_usr_local(
                         utils_selinux.transmogrify_sub_dirs(tmpdir)))
        needs_relabel = None  # Next run will catch if relabeling needed
    except utils_selinux.SelinuxError:  # Catchall SELinux related
        logging.info("SELinux not available, or error in command/setup.")
        logging.info("Please manually verify default file contexts before")
        logging.info("testing with SELinux enabled and enforcing.")
    if needs_relabel:
        if selinux:
            answer = "y"
        else:
            if interactive:
                answer = utils.ask("Relabel from default contexts?")
            else:
                answer = "n"
        if answer.lower() == 'y':
            changes = utils_selinux.apply_defcon(datadir, False)
            changes += utils_selinux.apply_defcon(imagesdir, True)
            changes += utils_selinux.apply_defcon(isosdir, True)
            changes += utils_selinux.apply_defcon(tmpdir, True)
            logging.info("Corrected contexts on %d files/dirs",
                         len(changes))


def bootstrap(test_name, test_dir, base_dir, default_userspace_paths,
              check_modules, online_docs_url, restore_image=False,
              download_image=True, interactive=True, selinux=False,
              verbose=False, update_providers=False,
              guest_os=defaults.DEFAULT_GUEST_OS):
    """
    Common virt test assistant module.

    :param test_name: Test name, such as "qemu".
    :param test_dir: Path with the test directory.
    :param base_dir: Base directory used to hold images and isos.
    :param default_userspace_paths: Important programs for a successful test
            execution.
    :param check_modules: Whether we want to verify if a given list of modules
            is loaded in the system.
    :param online_docs_url: URL to an online documentation system, such as a
            wiki page.
    :param restore_image: Whether to restore the image from the pristine.
    :param interactive: Whether to ask for confirmation.
    :param verbose: Verbose output.
    :param selinux: Whether setup SELinux contexts for shared/data.
    :param update_providers: Whether to update test providers if they are already
            downloaded.
    :param guest_os: Specify the guest image used for bootstrapping. By default
            the JeOS image is used.

    :raise error.CmdError: If JeOS image failed to uncompress
    :raise ValueError: If 7za was not found
    """
    if interactive:
        logging_manager.configure_logging(utils_misc.VirtLoggingConfig(),
                                          verbose=verbose)
    logging.info("%s test config helper", test_name)
    step = 0

    logging.info("")
    step += 1
    logging.info("%d - Updating all test providers", step)
    asset.download_all_test_providers(update_providers)

    logging.info("")
    step += 1
    logging.info("%d - Checking the mandatory programs and headers", step)
    verify_mandatory_programs(test_name)

    logging.info("")
    step += 1
    logging.info("%d - Checking the recommended programs", step)
    verify_recommended_programs(test_name)

    logging.info("")
    step += 1
    logging.info("%d - Verifying directories", step)
    shared_dir = os.path.dirname(data_dir.get_data_dir())
    sub_dir_list = ["images", "isos", "steps_data", "gpg"]
    for sub_dir in sub_dir_list:
        sub_dir_path = os.path.join(base_dir, sub_dir)
        if not os.path.isdir(sub_dir_path):
            logging.debug("Creating %s", sub_dir_path)
            os.makedirs(sub_dir_path)
        else:
            logging.debug("Dir %s exists, not creating",
                          sub_dir_path)

    datadir = data_dir.get_data_dir()
    if test_name == 'libvirt':
        create_config_files(test_dir, shared_dir, interactive, step)
        create_subtests_cfg(test_name)
        create_guest_os_cfg(test_name)
        # Don't bother checking if changes can't be made
        if os.getuid() == 0:
            verify_selinux(datadir,
                           os.path.join(datadir, 'images'),
                           os.path.join(datadir, 'isos'),
                           data_dir.get_tmp_dir(),
                           interactive, selinux)

    # lvsb test doesn't use any shared configs
    elif test_name == 'lvsb':
        create_subtests_cfg(test_name)
        if os.getuid() == 0:
            # Don't bother checking if changes can't be made
            verify_selinux(datadir,
                           os.path.join(datadir, 'images'),
                           os.path.join(datadir, 'isos'),
                           data_dir.get_tmp_dir(),
                           interactive, selinux)
    else:  # Some other test
        create_config_files(test_dir, shared_dir, interactive, step)
        create_subtests_cfg(test_name)
        create_guest_os_cfg(test_name)

    if download_image or restore_image:
        logging.info("")
        step += 2
        logging.info("%s - Verifying (and possibly downloading) guest image",
                     step)
        for os_info in get_guest_os_info_list(test_name, guest_os):
            os_asset = os_info['asset']
            asset.download_asset(os_asset, interactive=interactive,
                                 restore_image=restore_image)

    if check_modules:
        logging.info("")
        step += 1
        logging.info("%d - Checking for modules %s", step,
                     ", ".join(check_modules))
        for module in check_modules:
            if not utils.module_is_loaded(module):
                logging.warning("Module %s is not loaded. You might want to "
                                "load it", module)
            else:
                logging.debug("Module %s loaded", module)

    if online_docs_url:
        logging.info("")
        step += 1
        logging.info("%d - If you wish, take a look at the online docs for "
                     "more info", step)
        logging.info("")
        logging.info(online_docs_url)
