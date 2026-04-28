# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
#
# client/base_utils.py
#
# Copyright: 2022 IBM
# Authors : Naresh Bannoth <nbannoth@linux.vnet.ibm.com>


"""
Nvme utilities
"""


import json
import logging
import os
import re
import time

from avocado.utils import pci, process

LOGGER = logging.getLogger(__name__)


class NvmeException(Exception):
    """
    Base Exception Class for all exceptions
    """


def get_controller_name(pci_addr):
    """
    Returns the controller/Adapter name with the help of pci_address

    :param pci_addr: pci_address of the adapter
    :rtype: string
    :raises: :py:class:`NvmeException` on failure to find pci_address in OS
    """
    if pci_addr in pci.get_pci_addresses():
        path = f"/sys/bus/pci/devices/{pci_addr}/nvme/"
        return "".join(os.listdir(path))
    raise NvmeException("Unable to list as wrong pci_addr")


def get_max_ns_supported(controller_name):
    """
    Returns the number of namespaces supported for the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "nn":
            return int(line.split(":")[-1].strip())
    return ""


def get_total_capacity(controller_name):
    """
    Returns the total capacity of the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "tnvmcap":
            return int(line.split(":")[-1].strip())
    return ""


def get_controller_id(controll_name):
    """
    Returns the nvme controller id

    :param controller_name: Name of the controller eg: nvme0
    :rtype: string
    """
    cmd = f"nvme id-ctrl /dev/{controll_name}"
    output = process.run(cmd, shell=True, sudo=True, ignore_status=True).stdout_text
    for line in output.splitlines():
        if "cntlid" in line:
            return line.split(":")[-1].strip()
    return ""


def get_current_ns_ids(controller_name):
    """
    Returns the list of namespaces in the nvme controller

    :param controller_name: Name of the nvme controller like nvme0, nvme1
    :rtype: list
    """
    cmd = f"nvme list-ns /dev/{controller_name}"
    namespaces = []
    output = process.run(cmd, shell=True, sudo=True, ignore_status=True).stdout_text
    for line in output.splitlines():
        if line.startswith("["):
            # Format is: [   0]:0x1 where 0x1 is the namespace ID in hex
            if ':' in line:
                ns_id_hex = line.split(':')[-1].strip()
                # Convert hex string (e.g., '0x1') to integer
                try:
                    namespaces.append(int(ns_id_hex, 16))
                except ValueError:
                    # If not hex, try decimal
                    try:
                        namespaces.append(int(ns_id_hex))
                    except ValueError:
                        LOGGER.warning(f"Could not parse namespace ID from: {line}")
    return namespaces


def get_current_ns_list(controller_name, shared_ns=False):
    """
    Returns the list of namespaces in the nvme controller

    :param controller_name: Name of the nvme controller like nvme0, nvme1
    :rtype: list
    """
    namespace_list = []
    namespaces_ids = get_current_ns_ids(controller_name)
    if shared_ns:
        subsys = get_subsystem_using_ctrl_name(controller_name)
        controller_name = f"nvme{subsys[len('nvme-subsy'):]}"
    for ns_id in namespaces_ids:
        namespace_list.append(f"/dev/{controller_name}n{ns_id}")
    return namespace_list


def get_block_size(controller_name, shared_ns=False):
    """
    Returns the block size of the namespace.
    If not found, return defaults to 4k.

    :param namespace: Name of the namespace like /dev/nvme0n1 etc..
    :rtype: Integer
    """
    namespaces = get_current_ns_list(controller_name, shared_ns=shared_ns)
    if namespaces:
        namespace = get_namespace_absolute_path(namespaces[0])
        if shared_ns:
            subsys = get_subsystem_using_ctrl_name(controller_name)
            controller_name = f"nvme{subsys[len('nvme-subsy'):]}"
            ns_match = re.search(r"nvme\d+n(\d+)", namespace)
            if ns_match:
                namespace = f"{controller_name}n{ns_match.group(1)}"
                namespace = get_namespace_absolute_path(namespace)
        cmd = f"nvme id-ns {namespace}"
        out = process.run(cmd, shell=True, ignore_status=True).stdout_text
        for line in out.splitlines():
            if "in use" in line:
                return pow(2, int(line.split()[4].split(":")[-1]))
    return 4096


def get_namespace_absolute_path(namespace):
    """
    Returns absolute path for nvme namespace

    :rtype: String
    """
    if "dev" not in namespace:
        return f"/dev/{namespace}"
    return namespace


def delete_ns(controller_name, ns_id, shared_ns=False):
    """
    Deletes the specified namespace on the controller

    :param controller_name: Nvme controller name to which namespace belongs
    :param ns_id: namespace id to be deleted
    """
    cont_id = get_controller_id(controller_name)
    if shared_ns:
        ctrls = get_alternate_controller_name(controller_name)
        for ctrl in ctrls:
            cont_id = f"{cont_id},{get_controller_id(ctrl)}"
    detach_ns(controller_name, ns_id, cont_id)
    cmd = f"nvme delete-ns /dev/{controller_name} -n {ns_id}"
    if process.system(cmd, shell=True, ignore_status=True):
        raise NvmeException(f"/dev/{controller_name}n{ns_id} delete failed")
    if is_ns_exists(controller_name, ns_id):
        raise NvmeException("namespace still listed even after deleted")


def delete_all_ns(controller_name, shared_ns=False):
    """
    Deletes all the name spaces available on the given nvme controller

    :param controller_name: Nvme controller name eg : nvme0, nvme1 etc..
    """
    namespaces_ids = get_current_ns_ids(controller_name)
    for ns_id in namespaces_ids[::-1]:
        delete_ns(controller_name, ns_id, shared_ns=shared_ns)
        time.sleep(5)


def is_ns_exists(controller_name, ns_id):
    """
    Returns if that particular namespace exists on the controller or not

    :param controller_name: name of the controller on which we want to check
                            ns existence

    :returns: True if exists else False
    :rtype: boolean
    """
    ns_list = get_current_ns_ids(controller_name)
    if ns_id in ns_list:
        return True
    for ctrl in get_alternate_controller_name(controller_name):
        ns_list = get_current_ns_ids(ctrl)
        if ns_id in ns_list:
            return True
    return False


def get_lba(namespace, shared_ns=False):
    """
    Returns LBA of the namespace. If not found, return defaults to 0.

    :param namespace: nvme namespace like /dev/nvme0n1, /dev/nvme0n2 etc..
    :rtype: Integer
    """
    if namespace:
        if shared_ns:
            ns_match = re.search(r"(/dev/)?(nvme\d+)n\d+", namespace)
            if ns_match:
                ctrl_name = ns_match.group(2)
                subsys = get_subsystem_using_ctrl_name(ctrl_name)
                controller_name = f"nvme{subsys[len('nvme-subsy'):]}"
                ns_id_match = re.search(r"nvme\d+n(\d+)", namespace)
                if ns_id_match:
                    namespace = f"{controller_name}n{ns_id_match.group(1)}"
        namespace = get_namespace_absolute_path(namespace)
        cmd = f"nvme id-ns {namespace}"
        out = process.run(cmd, shell=True, ignore_status=True).stdout_text
        for line in out.splitlines():
            if "in use" in line:
                return int(line.split()[1])
    return 0


def ns_rescan(controller_name):
    """
    re-scans all the names spaces on the given controller

    :param controller_name: controller name on which re-scan is applied
    """
    cmd = f"nvme ns-rescan /dev/{controller_name}"
    try:
        process.run(cmd, shell=True, ignore_status=True)
    except process.CmdError as detail:
        LOGGER.debug(detail)


def detach_ns(controller_name, ns_id, cont_id):
    """
    detach the namespace_id to specified controller

    :param ns_id: namespace ID
    :param controller_name: controller name
    :param cont_id: controller_ID
    """
    cmd = f"nvme detach-ns /dev/{controller_name} --namespace-id={ns_id} --controllers={cont_id}"
    if not process.run(cmd, shell=True, ignore_status=True):
        raise NvmeException("detach command failed")
    ns_rescan(controller_name)
    time.sleep(5)
    if is_ns_exists(controller_name, ns_id):
        raise NvmeException("namespace detached but still listing")


def attach_ns(ns_id, controller_name, cont_id):
    """
    attach the namespace_id to specified controller

    :param ns_id: namespace ID (string or int)
    :param controller_name: controller name
    :param cont_id: controller_ID
    """
    # Ensure ns_id is an integer for consistent comparison
    ns_id = int(ns_id)
    cmd = f"nvme attach-ns /dev/{controller_name} --namespace-id={ns_id} -controllers={cont_id}"
    if not process.run(cmd, shell=True, ignore_status=True):
        raise NvmeException("namespaces attach command failed")
    ns_rescan(controller_name)
    # Add delay to allow kernel to update namespace list after rescan
    time.sleep(2)
    if not is_ns_exists(controller_name, ns_id):
        raise NvmeException("namespaces attached but not listing")


def get_supported_lba_formats(controller_name):
    """
    Query and return supported LBA formats for the NVMe controller.

    This function attempts to retrieve the LBA Format (LBAF) array from an
    existing namespace on the controller. The LBAF array is controller-wide,
    meaning all namespaces on the same controller share the same set of
    supported formats, though each namespace can select a different format.

    :param controller_name: Name of the controller (e.g., 'nvme0')
    :return: List of dicts containing format details, each with keys:
        'index', 'block_size', 'metadata_size', 'relative_performance', 'valid'
    :rtype: list
    :raises: NvmeException if unable to query formats
    """
    # Try to get formats from an existing namespace
    namespaces = get_current_ns_list(controller_name)
    
    if namespaces:
        # Query first available namespace for LBAF array
        namespace = get_namespace_absolute_path(namespaces[0])
        cmd = f"nvme id-ns {namespace} -o json"
        try:
            result = process.run(cmd, shell=True, ignore_status=False, sudo=True)
            ns_data = json.loads(result.stdout_text)
            
            # Extract and parse LBAF array
            lba_formats = []
            for idx, lbaf in enumerate(ns_data.get('lbafs', [])):
                # Check if format is valid (ds > 0 means valid data size)
                ds = lbaf.get('ds', 0)
                if ds > 0:
                    lba_formats.append({
                        'index': idx,
                        'block_size': 2 ** ds,  # Convert power-of-2 to actual size
                        'metadata_size': lbaf.get('ms', 0),
                        'relative_performance': lbaf.get('rp', 0),
                        'valid': True
                    })
            
            if lba_formats:
                LOGGER.debug(f"Found {len(lba_formats)} valid LBA formats for {controller_name}")
                return lba_formats
                
        except (process.CmdError, json.JSONDecodeError, KeyError) as e:
            LOGGER.warning(f"Failed to query LBA formats from namespace: {e}")
    
    # Fallback: If no namespace exists or query failed, return common formats
    # Most NVMe devices support at least 512B and 4KB formats at indices 0 and 1
    # This is a safe assumption based on NVMe specification common implementations
    LOGGER.warning(
        f"No namespace found on {controller_name}, using common format assumptions. "
        f"This fallback assumes FLBAS indices 0 and 1 are valid with 512B and 4KB blocks respectively."
    )
    return [
        {'index': 0, 'block_size': 512, 'metadata_size': 0,
         'relative_performance': 0, 'valid': True},
        {'index': 1, 'block_size': 4096, 'metadata_size': 0,
         'relative_performance': 0, 'valid': True}
    ]


def get_optimal_flbas(controller_name):
    """
    Determine the optimal FLBAS (Formatted LBA Size) index for namespace creation.
    
    FLBAS is a namespace-specific field (bits 3:0) that selects which LBA format
    from the controller's LBAF array should be used. This function implements
    an intelligent selection strategy:
    
    1. Prefer FLBAS index 0 if it's valid (most common default)
    2. If index 0 is invalid, select first format with metadata_size=0
    3. Among formats with no metadata, prefer common block sizes (512B, 4KB)
    
    :param controller_name: Name of the controller (e.g., 'nvme0')
    :return: FLBAS index (0-15) to use for namespace creation
    :rtype: int
    :raises: NvmeException if no valid format is found
    """
    try:
        formats = get_supported_lba_formats(controller_name)
        
        if not formats:
            raise NvmeException(f"No valid LBA formats found for {controller_name}")
        
        # Strategy 1: Try index 0 first (most common default)
        for fmt in formats:
            if fmt['index'] == 0 and fmt['valid']:
                LOGGER.info(f"Using FLBAS index 0 (block_size={fmt['block_size']}B) "
                           f"for {controller_name}")
                return 0
        
        # Strategy 2: Find first format with no metadata
        formats_no_metadata = [f for f in formats if f['metadata_size'] == 0]
        
        if formats_no_metadata:
            # Prefer common block sizes: 512B or 4KB
            for preferred_size in [512, 4096]:
                for fmt in formats_no_metadata:
                    if fmt['block_size'] == preferred_size:
                        LOGGER.info(f"Using FLBAS index {fmt['index']} "
                                   f"(block_size={fmt['block_size']}B) for {controller_name}")
                        return fmt['index']
            
            # If no preferred size found, use first format without metadata
            selected = formats_no_metadata[0]
            LOGGER.info(f"Using FLBAS index {selected['index']} "
                       f"(block_size={selected['block_size']}B) for {controller_name}")
            return selected['index']
        
        # Strategy 3: Last resort - use first valid format even with metadata
        selected = formats[0]
        LOGGER.warning(f"All formats have metadata. Using FLBAS index {selected['index']} "
                      f"(block_size={selected['block_size']}B, metadata={selected['metadata_size']}B)")
        return selected['index']
        
    except Exception as e:
        raise NvmeException(f"Failed to determine optimal FLBAS for {controller_name}: {e}")


def create_full_capacity_ns(controller_name, shared_ns=False):
    """
    Creates one namespace with full capacity

    :param controller_name: name of the controller like nvme0/nvme1 etc..
    """
    ns_size = get_total_capacity(controller_name) // get_block_size(controller_name)
    if get_current_ns_list(controller_name, shared_ns=shared_ns):
        raise NvmeException("ns already exist, delete it before creating ")
    create_one_ns("1", controller_name, ns_size, shared_ns=shared_ns)


def create_one_ns(ns_id, controller_name, ns_size, shared_ns=False, flbas=0):
    """
    Creates a single namespace with given size and controller_id.
    
    This function supports dynamic FLBAS (Formatted LBA Size) selection with
    intelligent fallback behavior:
    
    **FLBAS Selection Modes:**
    
    1. **Default Mode (flbas=0)**: Backward compatible behavior
       - First attempts namespace creation with FLBAS=0
       - If FLBAS=0 fails, automatically detects optimal FLBAS and retries
       - Recommended for most use cases
    
    2. **Auto-Detect Mode (flbas=-1)**: Skip FLBAS=0 attempt
       - Immediately detects and uses optimal FLBAS value
       - Useful for devices known to have non-standard FLBAS configurations
       - Saves one failed attempt on such devices
    
    3. **Explicit Mode (flbas=1-15)**: Use specific FLBAS index
       - Uses the specified FLBAS value without auto-detection
       - No retry on failure
       - For advanced users who know their device's FLBAS requirements

    :param ns_id: Namespace ID (typically 1-based)
    :param controller_name: Name of the controller like nvme0/nvme1 etc..
    :param ns_size: Size of the namespace in blocks (based on selected LBA format)
    :param shared_ns: Whether to create a shared namespace (default: False)
    :param flbas: FLBAS index to use:
                  - 0 (default): Try FLBAS=0, auto-retry on failure
                  - -1: Skip FLBAS=0, immediately use auto-detected optimal value
                  - 1-15: Use explicit FLBAS index, no auto-detection
    :raises: NvmeException if namespace creation fails with all attempted FLBAS values
    
    :example:
        # Standard usage (backward compatible)
        create_one_ns("1", "nvme0", 2097152)
        
        # Force auto-detection for non-standard devices
        create_one_ns("1", "nvme0", 2097152, flbas=-1)
        
        # Use explicit FLBAS value
        create_one_ns("1", "nvme0", 2097152, flbas=2)
    """
    # Determine retry strategy based on flbas parameter
    # Only enable auto-detection fallback for default flbas=0
    should_retry_with_auto_detect = (flbas == 0)
    
    # Handle explicit auto-detection request (flbas=-1)
    # This skips the FLBAS=0 attempt and goes straight to optimal detection
    if flbas == -1:
        try:
            flbas = get_optimal_flbas(controller_name)
            LOGGER.info(f"Auto-detected FLBAS={flbas} for namespace creation on {controller_name}")
        except NvmeException as e:
            LOGGER.error(f"Failed to auto-detect FLBAS: {e}")
            raise NvmeException(f"Cannot create namespace: FLBAS auto-detection failed: {e}")
    
    # Build and execute namespace creation command
    cmd = f"nvme create-ns /dev/{controller_name} --nsze={ns_size} --ncap={ns_size} --flbas={flbas} --dps=0"
    if shared_ns:
        cmd = f"{cmd} -m 1"
    
    result = process.system(cmd, shell=True, ignore_status=True)
    
    # Intelligent retry: If creation failed with default FLBAS=0, try auto-detection
    # This provides automatic fallback for devices with non-standard FLBAS configurations
    if result != 0 and should_retry_with_auto_detect:
        LOGGER.warning(f"Namespace creation failed with FLBAS=0 on {controller_name}")
        LOGGER.info("Attempting auto-detection of optimal FLBAS value...")
        
        try:
            optimal_flbas = get_optimal_flbas(controller_name)
            
            # Only retry if optimal FLBAS is different from what we tried
            if optimal_flbas != 0:
                LOGGER.info(f"Retrying with auto-detected FLBAS={optimal_flbas}")
                cmd = f"nvme create-ns /dev/{controller_name} --nsze={ns_size} --ncap={ns_size} --flbas={optimal_flbas} --dps=0"
                if shared_ns:
                    cmd = f"{cmd} -m 1"
                
                result = process.system(cmd, shell=True, ignore_status=True)
                
                if result == 0:
                    LOGGER.info(f"Namespace creation succeeded with FLBAS={optimal_flbas}")
                    flbas = optimal_flbas  # Update for logging
                else:
                    raise NvmeException(
                        f"Namespace creation failed with both FLBAS=0 and auto-detected FLBAS={optimal_flbas}. "
                        f"Command: {cmd}"
                    )
            else:
                raise NvmeException(
                    f"Namespace creation failed with FLBAS=0 and auto-detection also suggests FLBAS=0. "
                    f"Command: {cmd}"
                )
        except NvmeException as e:
            raise NvmeException(f"Namespace creation failed: {e}")
    elif result != 0:
        # Failed with user-specified FLBAS (not 0), don't retry
        raise NvmeException(
            f"Namespace create command failed with FLBAS={flbas}. "
            f"Command: {cmd}. Exit code: {result}"
        )
    
    # Attach namespace to controller(s)
    cont_id = get_controller_id(controller_name)
    if shared_ns:
        ctrls = get_alternate_controller_name(controller_name)
        for ctrl in ctrls:
            cont_id = f"{cont_id},{get_controller_id(ctrl)}"
    attach_ns(ns_id, controller_name, cont_id)


def create_max_ns(controller_name, force, shared_ns=False):
    """
    Creates maximum number of namespaces, with equal capacity

    :param controller_name: name of the controller like nvme0/nvme1 etc..
    :param force: if wants to create the namespace force, then pass force=True
    """
    if get_current_ns_list(controller_name, shared_ns=shared_ns) and not force:
        raise NvmeException("ns already exist, cannot create max_ns")
    max_ns = int(get_max_ns_supported(controller_name))
    ns_size = get_equal_ns_size(controller_name, max_ns)
    for ns_id in range(1, (max_ns + 1)):
        create_one_ns(str(ns_id), controller_name, ns_size)


def get_equal_ns_size(controller_name, ns_count):
    """
    It calculate and return the size of a namespace when want to create
    more than one namespace with equal sizes

    :param controller_name: name of the controller like nvme0/nvme1 etc...
    :param ns_count: Number of namespaces you want to create with equal sizes
                     it should be less than or equal to max ns supported
                     on the controller
    :rtype: integer
    """
    existing_ns_list = len(get_current_ns_ids(controller_name))
    max_ns = get_max_ns_supported(controller_name)
    if ns_count > (max_ns - existing_ns_list):
        raise NvmeException("required ns count is greater than max supported")
    free_space = get_free_space(controller_name)
    if free_space < 1000:
        raise NvmeException("available free space is less than 1GB")
    return int(((60 * (free_space // 4096)) // 100) // ns_count)


def get_free_space(controller_name):
    """
    Returns the total capacity of the nvme adapter

    :param controller_name: Name of the controller eg: nvme0
    :rtype: integer
    """
    cmd = f"nvme id-ctrl /dev/{controller_name}"
    out = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    for line in out.splitlines():
        if line.split(":")[0].strip() == "unvmcap":
            return int(line.split(":")[-1].strip())
    return 0


def create_namespaces(controller_name, ns_count, shared_ns=False):
    """
    creates equal n number of namespaces on the specified controller

    :param controller_name: name of the controller like nvme0
    :param ns_count: number of namespaces to be created
    """
    namespaces = get_current_ns_ids(controller_name)
    if namespaces:
        delete_all_ns(controller_name)
    blk_size = get_total_capacity(controller_name) // get_block_size(controller_name)
    ns_size = blk_size // (ns_count + 1)
    for ns_id in range(1, ns_count + 1):
        create_one_ns(ns_id, controller_name, ns_size, shared_ns=shared_ns)


def get_ns_status(controller_name, ns_id):
    """
    Returns the status of namespaces on the specified controller

    :param controller_name: name of the controller like nvme0
    :param ns_id: ID of namespace for which we need the status

    :rtype: list
    """
    stat = []
    cmd = f"nvme show-topology /dev/{controller_name} -o json"
    data = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    json_data = json.loads(data)
    for data in json_data:
        for subsystem in data["Subsystems"]:
            for namespace in subsystem["Namespaces"]:
                nsid = namespace["NSID"]
                for paths in namespace["Paths"]:
                    if nsid == ns_id and paths["Name"] == controller_name:
                        stat.extend([paths["State"], paths["ANAState"]])
    return stat


def get_nslist_with_pci(pci_address):
    """
    Fetches and returns list of namespaces for specified pci_address

    :param pci_address: pci_address of any nvme adapter

    :rtype: list
    """
    ns_list = []
    cmd = "nvme show-topology -o json"
    data = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    json_data = json.loads(data)
    for data in json_data:
        for subsystem in data["Subsystems"]:
            for namespace in subsystem["Namespaces"]:
                for paths in namespace["Paths"]:
                    if paths["Address"] == pci_address:
                        ns_list.append(namespace["NSID"])
    return ns_list


def get_nvme_subsystem():
    """
    Fetches subsystem data and returns dictionary of all subsystems

    :rtype: dict
    """
    cmd = "nvme list-subsys -o json"
    data = process.run(cmd, ignore_status=True, sudo=True, shell=True).stdout_text
    json_data = json.loads(data)
    subsystems_dict = {}
    for host in json_data:
        for subsystem in host.get("Subsystems", []):
            nqn = subsystem.get("NQN")
            if nqn:
                subsystem_data = {
                    "Name": subsystem.get("Name"),
                    "IOPolicy": subsystem.get("IOPolicy"),
                    "Type": subsystem.get("Type"),
                    "Paths": subsystem.get("Paths", []),
                }
                subsystems_dict[nqn] = subsystem_data
    return subsystems_dict


def get_controllers_with_nqn(nqn):
    """
    Fetches controllers from subsystem based on input Non-Volatile
    Memory Express Qualified Name

    :rtype: list
    """
    subsys_dict = get_nvme_subsystem().get(nqn)
    if not subsys_dict:
        return ""
    return [path["Name"] for path in subsys_dict["Paths"]]


def get_subsys_name_with_nqn(nqn):
    """
    Fetches subsystem name based on input Non-Volatile Memory Express
    Qualified Name

    :rtype: string
    """
    subsys_dict = get_nvme_subsystem().get(nqn)
    if not subsys_dict:
        return ""
    return subsys_dict["Name"]


def get_controllers_with_subsys(subsys):
    """
    Fetches controllers from nvme subsystem with input as subsystem name

    :rtype: list
    """
    subsys_dict = get_nvme_subsystem()
    subsys_arr = [
        sub_sys_val
        for sub_sys, sub_sys_val in subsys_dict.items()
        if sub_sys_val.get("Name") == subsys
    ]
    if not subsys_arr:
        return []
    return [path["Name"] for path in subsys_arr[0]["Paths"]]


def get_alternate_controller_name(ctrl):
    """
    Fetches other controller in a subsystem based on input controller

    :rtype: list
    """
    subsys_dict = get_nvme_subsystem()
    for device_nqn in subsys_dict:
        ctrls = get_controllers_with_nqn(device_nqn)
        if ctrl in ctrls:
            return ctrls.remove(ctrl) or ctrls
    return []


def get_subsystem_using_ctrl_name(ctrl):
    """
    Fetches subsystem name with controller name as input

    :rtype: string
    """
    subsys_dict = get_nvme_subsystem()
    for device_nqn in subsys_dict:
        ctrls = get_controllers_with_nqn(device_nqn)
        if ctrl in ctrls:
            return get_subsys_name_with_nqn(device_nqn)
    return ""
