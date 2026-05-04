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
#
# Copyright: 2021 Red Hat Inc.
# Authors : Beraldo Leal <bleal@redhat.com>
# Authors : Abdul Haleem <abdhalee@linux.vnet.ibm.com

"""
This module provides an basic API for interacting with podman.

This module it was designed to be executed in async mode. Remember this when
consuming this API.
"""

import asyncio
import datetime
import json
import logging
import os
import subprocess
import time
from asyncio import create_subprocess_exec
from asyncio import subprocess as asyncio_subprocess
from pathlib import Path
from shutil import which

LOG = logging.getLogger(__name__)


def setup_user_and_group(username, password, spyre_group, log=None):
    """
    Setup user and manage group membership for non-root container execution.

    :param username: Username to setup (None or "root" for root user)
    :param password: Password for user (not used for root)
    :param spyre_group: Group name to add user to (e.g., "spyre_group")
    :param log: Logger instance (optional)
    :return: None
    """
    if log is None:
        log = LOG

    if username is None or username == "root":
        if spyre_group:
            log.info("Add root user to %s group", spyre_group)
            subprocess.run(f"usermod -aG {spyre_group} root",
                           shell=True, check=False)
    else:
        # Check if user exists
        user_check = subprocess.run(
            f"id -u {username} 2>/dev/null",
            shell=True, capture_output=True, check=False
        )

        if user_check.returncode != 0:
            log.info("Create user: %s", username)
            subprocess.run(f"useradd -m {username}", shell=True, check=False)
            subprocess.run(f"echo '{username}:{password}' | chpasswd",
                           shell=True, check=False)

        if spyre_group:
            log.info("Add %s to %s group", username, spyre_group)
            subprocess.run(f"usermod -aG {spyre_group} {username}",
                           shell=True, check=False)

def get_container_port(container_id, port=8000, user=None, log=None):
    """
    Get the actual host port mapped to a container port.

    :param container_id: Container ID
    :param port: Container port to check (default: 8000)
    :param user: Username if container was created by specific user
    :param log: Logger instance (optional)
    :return: Host port number or None
    """
    if log is None:
        log = LOG

    try:
        if user and user != "root":
            # Escape single quotes for su -c
            port_cmd = f"XDG_RUNTIME_DIR=/run/user/$(id -u) podman port {container_id} {port}"
            escaped_cmd = port_cmd.replace("'", "'\"'\"'")
            cmd = f"su - {user} -c '{escaped_cmd}'"
        else:
            cmd = f"podman port {container_id} {port}"

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            port_output = result.stdout.strip()
            log.info("Port mapping output: %s", port_output)

            if port_output and ":" in port_output:
                host_port = port_output.strip().split(":")[-1]
                log.info(
                    "Container port %d is mapped to host port: %s", port, host_port)
                return int(host_port)
            else:
                log.warning(
                    "Could not parse port from output: %s", port_output)
                return None
        else:
            log.error("Failed to get container port: %s", result.stderr)
            return None
    except Exception as ex:
        log.error("Failed to get container port: %s", ex)
        return None


def save_container_logs(container_id, log_dir, test_name="test", user=None, log=None):
    """
    Save complete container logs to a file.

    :param container_id: Container ID
    :param log_dir: Directory to save logs
    :param test_name: Test name for log file naming (default: "test")
    :param user: Username if container was created by specific user
    :param log: Logger instance (optional)
    :return: Path to saved log file or None
    """
    if log is None:
        log = LOG

    try:
        # Create logs directory
        logs_dir = os.path.join(log_dir, "container_logs")
        os.makedirs(logs_dir, exist_ok=True)

        # Generate log filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        log_filename = f"{test_name}_{container_id[:12]}_{timestamp}.log"
        log_filepath = os.path.join(logs_dir, log_filename)

        log.info("Saving complete container logs to: %s", log_filepath)

        # Get complete logs based on user context
        if user and user != "root":
            log_cmd = f"XDG_RUNTIME_DIR=/run/user/$(id -u) podman logs {container_id}"
            escaped_cmd = log_cmd.replace("'", "'\"'\"'")
            cmd = f"su - {user} -c '{escaped_cmd}'"
        else:
            cmd = f"podman logs {container_id}"

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=False, timeout=60
        )

        if result.returncode == 0:
            log_content = result.stdout
        else:
            log_content = f"Error retrieving logs:\n{result.stderr}\n\nPartial stdout:\n{result.stdout}"

        # Save logs to file
        with open(log_filepath, 'w', encoding='utf-8') as f:
            f.write(f"Container ID: {container_id}\n")
            f.write(f"Test Name: {test_name}\n")
            f.write(f"User: {user if user else 'root'}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("=" * 80 + "\n\n")
            f.write(log_content)

        log.info("Container logs saved successfully (%d bytes)", len(log_content))
        return log_filepath

    except subprocess.TimeoutExpired:
        log.warning("Timeout while retrieving container logs")
        return None
    except Exception as ex:
        log.warning("Failed to save container logs: %s", ex)
        return None



def install_huggingface_cli():
    """
    Install Hugging Face CLI if not already installed.

    :return: True if installed successfully, False otherwise
    """
    try:
        # Check if huggingface-cli is already available
        hf_cli_path = which("hf")
        if hf_cli_path:
            LOG.info("Hugging Face CLI already installed at: %s", hf_cli_path)
            try:
                result = subprocess.run(
                    [hf_cli_path, "--version"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10
                )
                if result.returncode == 0:
                    LOG.info("Hugging Face CLI version: %s",
                             result.stdout.strip())
                    return True
            except Exception as e:
                LOG.warning("Could not verify HF CLI version: %s", e)
                return True  # CLI exists, assume it works

        LOG.info("Hugging Face CLI not found, installing...")

        # Try to install using pip
        pip_path = which("pip") or which("pip3")
        if not pip_path:
            LOG.error("pip not found, cannot install Hugging Face CLI")
            return False

        LOG.info("Installing huggingface_hub[cli] using: %s", pip_path)
        result = subprocess.run(
            [pip_path, "install", "-U", "huggingface_hub[cli]"],
            capture_output=True,
            text=True,
            check=False,
            timeout=300
        )

        if result.returncode == 0:
            LOG.info("Hugging Face CLI installed successfully")
            LOG.debug("Installation output: %s", result.stdout)

            # Verify installation
            hf_cli_path = which("hf")
            if hf_cli_path:
                LOG.info("Verified: huggingface-cli found at %s", hf_cli_path)
                return True
            else:
                LOG.warning("huggingface-cli installed but not found in PATH")
                # Try common installation paths
                common_paths = [
                    os.path.expanduser("~/.local/bin/hf"),
                    "/usr/local/bin/hf",
                    "/usr/bin/hf"
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        LOG.info("Found huggingface-cli at: %s", path)
                        return True
                return False
        else:
            LOG.error("Failed to install Hugging Face CLI")
            LOG.error("Error output: %s", result.stderr)
            return False

    except subprocess.TimeoutExpired:
        LOG.error("Timeout while installing Hugging Face CLI")
        return False
    except Exception as ex:
        LOG.error("Error installing Hugging Face CLI: %s", ex)
        return False

def download_model_from_hf(hf_model_id, local_dir, model_name):
    """
    Download a model from Hugging Face Hub.

    :param hf_model_id: Hugging Face model ID (e.g., 'ibm-granite/granite-3.3-8b-instruct')
    :param local_dir: Local directory to download the model
    :param model_name: Local model directory name
    :return: True if download successful, False otherwise
    """
    try:
        model_path = os.path.join(local_dir, model_name)

        if os.path.exists(model_path) and os.listdir(model_path):
            LOG.info("Model already exists at: %s", model_path)
            contents = os.listdir(model_path)
            LOG.info("Model directory contains %d files/folders", len(contents))
            return True

        if not os.path.exists(local_dir):
            LOG.info("Creating models directory: %s", local_dir)
            os.makedirs(local_dir, exist_ok=True)

        LOG.info("Downloading model from Hugging Face Hub...")
        LOG.info("  Model ID: %s", hf_model_id)
        LOG.info("  Destination: %s", model_path)

        result = subprocess.run(
            ["hf", "download", "--local-dir", model_path, hf_model_id],
            capture_output=True,
            text=True,
            timeout=3600,
            check=False,
        )

        if result.returncode == 0:
            LOG.info("Model downloaded successfully")
            if os.path.exists(model_path):
                contents = os.listdir(model_path)
                LOG.info("Downloaded model contains %d files/folders:", len(contents))
                for item in contents[:10]:  # Show first 10 items
                    LOG.info("  - %s", item)
                if len(contents) > 10:
                    LOG.info("  ... and %d more items", len(contents) - 10)
                return True
            else:
                LOG.error("Model directory not found after download")
                return False
        else:
            LOG.error("Failed to download model. Exit code: %d", result.returncode)
            if result.stderr:
                LOG.error("Error output: %s", result.stderr)
            return False

    except Exception as ex:
        LOG.error("Error downloading model: %s", ex)
        return False

def validate_model_with_sha(model_path):
    """
    Validate model files by checking SHA256 checksums if available.

    :param model_path: Path to the model directory
    :return: Tuple of (is_valid, validation_messages)
    """
    import hashlib
    import glob
    validation_messages = []
    is_valid = True
    required_files = [
        "config.json",
        "tokenizer.json",
        "tokenizer_config.json"
    ]
    for req_file in required_files:
        file_path = os.path.join(model_path, req_file)
        if not os.path.exists(file_path):
            validation_messages.append(f"MISSING: {req_file}")
            is_valid = False
        elif os.path.getsize(file_path) == 0:
            validation_messages.append(f"EMPTY: {req_file}")
            is_valid = False
        else:
            validation_messages.append(
                f"OK: {req_file} ({os.path.getsize(file_path)} bytes)")
    weight_patterns = ["*.safetensors", "*.bin", "pytorch_model*.bin"]
    weight_files = []
    for pattern in weight_patterns:
        weight_files.extend(glob.glob(os.path.join(model_path, pattern)))
    if not weight_files:
        validation_messages.append("MISSING: No model weight files found")
        is_valid = False
    else:
        validation_messages.append(f"Found {len(weight_files)} weight file(s)")
        for weight_file in weight_files:
            file_size = os.path.getsize(weight_file)
            if file_size == 0:
                validation_messages.append(
                    f"EMPTY: {os.path.basename(weight_file)}")
                is_valid = False
            else:
                validation_messages.append(
                    f"OK: {os.path.basename(weight_file)} ({file_size} bytes)")
    sha_file = os.path.join(model_path, ".gitattributes")
    if not os.path.exists(sha_file):
        sha_file = os.path.join(model_path, "SHA256SUMS")

    if os.path.exists(sha_file):
        validation_messages.append(
            f"Found checksum file: {os.path.basename(sha_file)}")
        try:
            with open(sha_file, 'r') as f:
                sha_content = f.read()
            for weight_file in weight_files:
                filename = os.path.basename(weight_file)
                if filename in sha_content:
                    validation_messages.append(
                        f"Validating SHA256 for: {filename}")
                    sha256_hash = hashlib.sha256()
                    try:
                        with open(weight_file, "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                        actual_sha = sha256_hash.hexdigest()
                        if actual_sha[:16] in sha_content:
                            validation_messages.append(
                                f"SHA256 VALID: {filename}")
                        else:
                            validation_messages.append(
                                f"SHA256 MISMATCH: {filename}")
                            validation_messages.append(
                                f"  Calculated: {actual_sha[:16]}...")
                            is_valid = False
                    except Exception as sha_ex:
                        validation_messages.append(
                            f"SHA256 calculation failed for {filename}: {sha_ex}")
        except Exception as ex:
            validation_messages.append(f"Failed to read checksum file: {ex}")
    else:
        validation_messages.append(
            "No checksum file found - skipping SHA validation")

    return is_valid, validation_messages


class PodmanException(Exception):
    pass


class _Podman:

    PYTHON_VERSION_COMMAND = json.dumps(
        [
            "/usr/bin/env",
            "python3",
            "-c",
            (
                "import sys; print(sys.version_info.major, "
                "sys.version_info.minor, sys.executable)"
            ),
        ]
    )

    def __init__(self, podman_bin=None):
        path = which(podman_bin or "podman")
        if not path:
            msg = f"Podman binary {podman_bin} is not available on the system."
            raise PodmanException(msg)

        self.podman_bin = path


class Podman(_Podman):
    def execute(self, *args):
        """Execute a command and return the returncode, stdout and stderr.

        :param args: Variable length argument list to be used as argument
                      during execution.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            LOG.debug("Executing %s", args)

            cmd = [self.podman_bin, *args]
            with subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as proc:
                stdout, stderr = proc.communicate()
                LOG.debug("Return code: %s", proc.returncode)
                LOG.debug("Stdout: %s", stdout.decode("utf-8", "replace"))
                LOG.debug("Stderr: %s", stderr.decode("utf-8", "replace"))
                if proc.returncode:
                    command_args = " ".join(args)
                    msg = f'Failure from command "{self.podman_bin} {command_args}": returned code "{proc.returncode}" stderr: "{stderr}"'
                    LOG.error(msg)
                    raise PodmanException(msg)

                return proc.returncode, stdout, stderr
        except (FileNotFoundError, PermissionError) as ex:
            msg = "Could not execute the command."
            LOG.error("%s: %s", msg, str(ex))
            raise PodmanException(msg) from ex

    def copy_to_container(self, container_id, src, dst):
        """Copy artifacts from src to container:dst.

        This method allows copying the contents of src to the dst. Files will
        be copied from the local machine to the container. The "src" argument
        can be a file or a directory.

        :param str container_id: string with the container identification.
        :param str src: what file or directory you are trying to copy.
        :param str dst: the destination inside the container.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("cp", src, f"{container_id}:{dst}")
        except PodmanException as ex:
            error = f"Failed copying data to container {container_id}"
            LOG.error(error)
            raise PodmanException(error) from ex

    def get_python_version(self, image):
        """Return the current Python version installed in an image.

        :param str image: Image name. i.e: 'fedora:33'.
        :rtype: tuple with both: major, minor numbers and executable path.
        """
        try:
            _, stdout, _ = self.execute(
                "run", "--rm", f"--entrypoint={self.PYTHON_VERSION_COMMAND}", image
            )
        except PodmanException as ex:
            raise PodmanException("Failed getting Python version.") from ex

        if stdout:
            output = stdout.decode().strip().split()
            return int(output[0]), int(output[1]), output[2]
        return None

    def get_container_info(self, container_id):
        """Return all information about specific container.

        :param container_id: identifier of container
        :type container_id: str
        :rtype: dict
        """
        try:
            _, stdout, _ = self.execute(
                "ps", "--all", "--format=json", "--filter", f"id={container_id}"
            )
        except PodmanException as ex:
            raise PodmanException(
                f"Failed getting information about container: {container_id}."
            ) from ex
        containers = json.loads(stdout.decode())
        for container in containers:
            if container.get("Id") == container_id:
                return container
        return {}

    def start(self, container_id):
        """Starts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to start.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("start", container_id)
        except PodmanException as ex:
            raise PodmanException("Failed to start the container.") from ex

    def stop(self, container_id):
        """Stops a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to stop.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("stop", "-t=0", container_id)
        except PodmanException as ex:
            raise PodmanException("Failed to stop the container.") from ex

    def restart(self, container_id, timeout=10):
        """Restarts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to restart.
        :param int timeout: Timeout in seconds to wait for container to stop before killing it (default: 10).
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("restart", f"-t={timeout}", container_id)
        except PodmanException as ex:
            raise PodmanException("Failed to restart the container.") from ex

    def exec_command(
        self,
        container_id,
        command,
        user=None,
        workdir=None,
        env=None,
        interactive=False,
        tty=False,
    ):
        """Execute a command in a running container.

        :param str container_id: Container identification string.
        :param str or list command: Command to execute. Can be a string or list of arguments.
        :param str user: Optional user to run the command as (e.g., "root", "1000", "1000:1000").
        :param str workdir: Optional working directory for the command.
        :param dict env: Optional dictionary of environment variables to set.
        :param bool interactive: Keep STDIN open even if not attached (default: False).
        :param bool tty: Allocate a pseudo-TTY (default: False).
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            cmd_args = ["exec"]

            if interactive:
                cmd_args.append("-i")
            if tty:
                cmd_args.append("-t")
            if user is not None:
                cmd_args.extend(["-u", user])
            if workdir is not None:
                cmd_args.extend(["-w", workdir])
            if env is not None:
                for key, value in env.items():
                    cmd_args.extend(["-e", f"{key}={value}"])

            cmd_args.append(container_id)

            if isinstance(command, str):
                cmd_args.extend(command.split())
            elif isinstance(command, list):
                cmd_args.extend(command)
            else:
                raise PodmanException("Command must be a string or list")

            return self.execute(*cmd_args)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to execute command in container {container_id}."
            ) from ex

    def collect_container_aiu_metrics(
        self,
        container_id,
        output_file,
        dtcompiler_export_dir=None,
        stats_command="aiu-smi --csv",
        timeout=None,
    ):
        """
        Start collecting AIU metrics from a container in the background using nohup.

        This method runs a podman exec command in the background to continuously
        collect AIU metrics from a running container.

        :param str container_id: Container identification string.
        :param str output_file: Path to output file where stats will be saved (e.g., /path/to/aiu_metrics.csv).
        :param str dtcompiler_export_dir: Optional DTCOMPILER_EXPORT_DIR environment variable value.
        :param str stats_command: Command to run inside container for collecting stats
                                  (default: "aiu-smi --csv").
        :param int timeout: Optional timeout in seconds. If specified, stats collection will automatically
                           stop after this duration. If None, collection runs indefinitely.
        :return: Process object for the background process.
        :rtype: subprocess.Popen
        """
        try:
            podman_cmd = [self.podman_bin, "exec"]

            if dtcompiler_export_dir:
                podman_cmd.extend(
                    ["-e", f"DTCOMPILER_EXPORT_DIR={dtcompiler_export_dir}"]
                )

            podman_cmd.append(container_id)

            podman_cmd.extend(["bash", "--login", "-c", stats_command])

            if timeout:
                full_command = f"nohup bash -c 'timeout {timeout} {' '.join(podman_cmd)} | tee {output_file}' > /dev/null 2>&1 &"
                LOG.info(
                    "Starting background stats collection with %d second timeout: %s",
                    timeout,
                    full_command,
                )
            else:
                full_command = f"nohup bash -c '{' '.join(podman_cmd)} | tee {output_file}' > /dev/null 2>&1 &"
                LOG.info(
                    "Starting background stats collection (no timeout): %s",
                    full_command,
                )

            process = subprocess.Popen(
                full_command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            LOG.info("Background stats collection started with PID: %s", process.pid)
            return process

        except Exception as ex:
            error_msg = f"Failed to start background stats collection for container {container_id}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    def collect_container_stats(
        self, container_id, output_dir, interval=1, duration=60
    ):
        """
        Collect Podman CPU and memory stats and write as JSON.

        This method periodically collects container statistics (CPU and memory usage)
        and saves them to a JSON file for analysis. Supports collecting stats for a
        specific container or all running containers.

        :param str container_id: Container identification string or "all" for all containers.
        :param str output_dir: Base directory where stats JSON files will be saved.
                              Container-specific subdirectories will be created.
        :param int interval: Interval in seconds between stat collections (default: 1).
        :param int duration: Total duration in seconds to collect stats (default: 60).
        :return: Path to the generated JSON stats file (or list of paths if container_id="all").
        :rtype: str or list
        """
        try:
            if container_id.lower() == "all":
                _, stdout, _ = self.execute("ps", "--format", "{{.ID}}")
                container_ids = stdout.decode().strip().split("\n")
                container_ids = [cid.strip() for cid in container_ids if cid.strip()]

                if not container_ids:
                    LOG.warning("No running containers found")
                    return []

                LOG.info("Collecting stats for %d containers", len(container_ids))

                json_files = []
                for cid in container_ids:
                    json_file = self._collect_single_container_stats(
                        cid, output_dir, interval, duration
                    )
                    json_files.append(json_file)

                return json_files
            else:
                return self._collect_single_container_stats(
                    container_id, output_dir, interval, duration
                )

        except Exception as ex:
            error_msg = f"Failed to collect stats for container(s): {container_id}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    def _collect_single_container_stats(
        self, container_id, base_output_dir, interval, duration
    ):
        """
        Internal method to collect stats for a single container.

        :param str container_id: Container identification string.
        :param str base_output_dir: Base directory for output.
        :param int interval: Interval between collections.
        :param int duration: Total duration.
        :return: Path to JSON stats file.
        :rtype: str
        """
        try:
            container_output_dir = os.path.join(base_output_dir, container_id)
            Path(container_output_dir).mkdir(parents=True, exist_ok=True)
            json_file = os.path.join(container_output_dir, f"{container_id}_stats.json")

            all_stats = []
            end_time = time.time() + duration

            LOG.info(
                "Starting stats collection for container %s (duration: %ds, interval: %ds)",
                container_id,
                duration,
                interval,
            )

            while time.time() < end_time:
                try:
                    _, stdout, stderr = self.execute(
                        "stats", "--no-stream", "--format", "json", container_id
                    )

                    if stderr:
                        LOG.warning(
                            "[%s] stderr: %s", container_id, stderr.decode().strip()
                        )
                        time.sleep(interval)
                        continue

                    stats_list = json.loads(stdout.decode())
                    if stats_list:
                        stats = stats_list[0]
                        entry = {
                            "timestamp": datetime.datetime.utcnow().isoformat(),
                            "cpu_percent": stats.get("cpu_percent", ""),
                            "mem_percent": stats.get("mem_percent", ""),
                            "mem_usage": stats.get("mem_usage", ""),
                            "net_io": stats.get("net_io", ""),
                            "block_io": stats.get("block_io", ""),
                            "pids": stats.get("pids", ""),
                        }
                        all_stats.append(entry)
                        LOG.debug(
                            "[%s] CPU: %s%%, MEM: %s%%",
                            container_id,
                            entry["cpu_percent"],
                            entry["mem_percent"],
                        )

                except json.JSONDecodeError as je:
                    LOG.error("[%s] Failed to parse stats JSON: %s", container_id, je)
                except PodmanException as pe:
                    LOG.error("[%s] Failed to get stats: %s", container_id, pe)

                time.sleep(interval)

            with open(json_file, "w", encoding="utf-8") as jf:
                json.dump(all_stats, jf, indent=2)

            LOG.info(
                "[%s] Collected %d stat entries → %s",
                container_id,
                len(all_stats),
                json_file,
            )
            return json_file

        except Exception as ex:
            error_msg = f"Failed to collect stats for container {container_id}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    def send_vllm_inference_request(
        self,
        port,
        model_path,
        prompt,
        max_tokens=512,
        temperature=1.0,
        system_message="You are a helpful AI assistant.",
        host="127.0.0.1",
        use_jq=True,
    ):
        """
        Send an inference request to VLLM server using curl.

        This method sends a chat completion request to a running VLLM container
        and returns the response.

        :param int port: Port number where VLLM server is listening.
        :param str model_path: Model path as configured in VLLM (e.g., "/models/granite-3.3-8b-instruct").
        :param str prompt: User prompt/query to send to the model.
        :param int max_tokens: Maximum number of tokens to generate (default: 512).
        :param float temperature: Sampling temperature (default: 1.0).
        :param str system_message: System message to set context (default: "You are a helpful AI assistant.").
        :param str host: Host address (default: "127.0.0.1").
        :param bool use_jq: Whether to pipe output through jq for formatting (default: True).
        :return: Tuple of (returncode, response_text, error_text).
        :rtype: tuple
        """
        try:
            payload = {
                "model": model_path,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
            }

            payload_json = json.dumps(payload)

            url = f"http://{host}:{port}/v1/chat/completions"

            curl_cmd = [
                "curl",
                url,
                "-H",
                "Content-Type: application/json",
                "-d",
                payload_json,
            ]

            if use_jq:
                curl_cmd_str = " ".join(
                    [f"'{arg}'" if " " in arg else arg for arg in curl_cmd]
                )
                full_cmd = f"{curl_cmd_str} | jq"
                LOG.info("Sending inference request: %s", full_cmd)
            else:
                full_cmd = curl_cmd
                LOG.info("Sending inference request to %s", url)

            result = subprocess.run(
                full_cmd if use_jq else curl_cmd,
                shell=use_jq,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for inference
                check=False,
            )

            if result.returncode == 0:
                LOG.info("Inference request successful")
                LOG.debug("Response: %s", result.stdout[:500])
            else:
                LOG.error("Inference request failed with code %d", result.returncode)
                LOG.error("Error: %s", result.stderr)

            return result.returncode, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = "Inference request timed out after 300 seconds"
            LOG.error(error_msg)
            raise PodmanException(error_msg)
        except Exception as ex:
            error_msg = f"Failed to send inference request to {host}:{port}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    def run_vllm_container(
        self,
        image,
        aiu_ids,
        host_models_dir,
        vllm_model_path,
        aiu_world_size,
        max_model_len,
        max_batch_size,
        memory="100G",
        shm_size="2G",
        device="/dev/vfio",
        privileged="true",
        pids_limit="0",
        userns="keep-id",
        group_add="keep-groups",
        port_mapping="127.0.0.1::8000",
        vllm_spyre_use_cb=None,
        vllm_dt_chunk_len=None,
        vllm_spyre_use_chunked_prefill=None,
        enable_prefix_caching=None,
        max_num_batched_tokens=None,
        additional_vllm_args=None,
        container_name=None,
        user=None,
        dtlog_level=None,
        dtcompiler_keep_export=None,
        vllm_spyre_require_precompiled_decoders=None,
        enable_flex_timing=None,
        flex_print_end_to_end_breakdown=None,
        flex_skip_timestamp_calibration=None,
        flex_scheduler_print_raw_timestamps=None,
        flex_global_profile_prefix=None,
    ):
        """Run a VLLM container with AIU support.

        :param str image: Container image to run.
        :param str aiu_ids: Space-separated AIU PCIe IDs.
        :param str host_models_dir: Host directory containing models.
        :param str vllm_model_path: Path to model inside container.
        :param int aiu_world_size: AIU world size (tensor parallelism).
        :param int max_model_len: Maximum model length.
        :param int max_batch_size: Maximum batch size.
        :param str memory: Memory limit (default: "100G" - adjust based on model size).
        :param str shm_size: Shared memory size (default: "2G" - increase for larger batches).
        :param str device: Device to mount (default: "/dev/vfio").
        :param str privileged: Run in privileged mode (default: "true").
        :param str pids_limit: PIDs limit (default: "0" - unlimited).
        :param str userns: User namespace mode (default: "keep-id").
        :param str group_add: Group add mode (default: "keep-groups").
        :param str port_mapping: Port mapping in format
            ``[host_ip]:[host_port]:container_port`` (default:
            ``"127.0.0.1::8000"`` - localhost with random host port to
            container port 8000). Examples:
            ``"127.0.0.1:8000:8000"`` (fixed host port 8000),
            ``"0.0.0.0::8000"`` (all interfaces, random host port),
            ``"::8000"`` (all interfaces, random host port).
        :param str vllm_spyre_use_cb: Optional VLLM Spyre use CB flag (e.g., "1"). If None, not set.
        :param int vllm_dt_chunk_len: Optional DT chunk length. If None, not set.
        :param int vllm_spyre_use_chunked_prefill: Optional chunked prefill flag. If None, not set.
        :param bool enable_prefix_caching: Optional enable VLLM prefix caching. If None, not set.
        :param int max_num_batched_tokens: Optional maximum number of batched tokens. If None, not set.
        :param list additional_vllm_args: Additional VLLM command-line arguments as list of strings.
        :param str container_name: Optional container name.
        :param str user: Optional user to run container as (e.g., "1000:1000").
        :param str dtlog_level: Optional DT log level (e.g., "warning"). If None, not set.
        :param str dtcompiler_keep_export: Optional DT compiler keep export flag (e.g., "true"). If None, not set.
        :param str vllm_spyre_require_precompiled_decoders: Optional require precompiled decoders flag (e.g., "0"). If None, not set.
        :param str enable_flex_timing: Optional enable flex timing flag (e.g., "0"). If None, not set.
        :param str flex_print_end_to_end_breakdown: Optional flex print end-to-end breakdown flag (e.g., "0"). If None, not set.
        :param str flex_skip_timestamp_calibration: Optional flex skip timestamp calibration flag (e.g., "0"). If None, not set.
        :param str flex_scheduler_print_raw_timestamps: Optional flex scheduler print raw timestamps flag (e.g., "0"). If None, not set.
        :param str flex_global_profile_prefix: Optional flex global profile prefix (e.g., "flex-logs"). If None, not set.
        :rtype: tuple with returncode, stdout (container ID), stderr.
        """
        cmd_args = [
            "run",
            "-d",
            "-it",
            f"--device={device}",
            "-v",
            f"{host_models_dir}:/models",
            "-e",
            f"AIU_PCIE_IDS={aiu_ids}",
            f"--privileged={privileged}",
            "--pids-limit",
            pids_limit,
            f"--userns={userns}",
            f"--group-add={group_add}",
            "--memory",
            memory,
            "--shm-size",
            shm_size,
            "-p",
            port_mapping,
        ]

        if vllm_spyre_use_cb is not None:
            cmd_args.extend(["-e", f"VLLM_SPYRE_USE_CB={vllm_spyre_use_cb}"])
        if vllm_dt_chunk_len is not None:
            cmd_args.extend(["-e", f"VLLM_DT_CHUNK_LEN={vllm_dt_chunk_len}"])
        if vllm_spyre_use_chunked_prefill is not None:
            cmd_args.extend(
                [
                    "-e",
                    f"VLLM_SPYRE_USE_CHUNKED_PREFILL={vllm_spyre_use_chunked_prefill}",
                ]
            )

        if dtlog_level is not None:
            cmd_args.extend(["-e", f"DTLOG_LEVEL={dtlog_level}"])
        if dtcompiler_keep_export is not None:
            cmd_args.extend(["-e", f"DTCOMPILER_KEEP_EXPORT={dtcompiler_keep_export}"])
        if vllm_spyre_require_precompiled_decoders is not None:
            cmd_args.extend(
                [
                    "-e",
                    f"VLLM_SPYRE_REQUIRE_PRECOMPILED_DECODERS={vllm_spyre_require_precompiled_decoders}",
                ]
            )
        if enable_flex_timing is not None:
            cmd_args.extend(["-e", f"ENABLE_FLEX_TIMING={enable_flex_timing}"])
        if flex_print_end_to_end_breakdown is not None:
            cmd_args.extend(
                [
                    "-e",
                    f"FLEX_PRINT_END_TO_END_BREAKDOWN={flex_print_end_to_end_breakdown}",
                ]
            )
        if flex_skip_timestamp_calibration is not None:
            cmd_args.extend(
                [
                    "-e",
                    f"FLEX_SKIP_TIMESTAMP_CALIBRATION={flex_skip_timestamp_calibration}",
                ]
            )
        if flex_scheduler_print_raw_timestamps is not None:
            cmd_args.extend(
                [
                    "-e",
                    f"FLEX_SCHEDULER_PRINT_RAW_TIMESTAMPS={flex_scheduler_print_raw_timestamps}",
                ]
            )
        if flex_global_profile_prefix is not None:
            cmd_args.extend(
                ["-e", f"FLEX_GLOBAL_PROFILE_PREFIX={flex_global_profile_prefix}"]
            )

        if user is not None:
            cmd_args.extend(["--user", user])

        if container_name:
            cmd_args.extend(["--name", container_name])

        cmd_args.extend(
            [
                image,
                "--model",
                vllm_model_path,
                "-tp",
                str(aiu_world_size),
                "--max-model-len",
                str(max_model_len),
                "--max-num-seqs",
                str(max_batch_size),
            ]
        )

        if enable_prefix_caching is not None and enable_prefix_caching:
            cmd_args.append("--enable-prefix-caching")

        if max_num_batched_tokens is not None:
            cmd_args.extend(["--max-num-batched-tokens", str(max_num_batched_tokens)])

        if additional_vllm_args:
            cmd_args.extend(additional_vllm_args)

        try:
            return self.execute(*cmd_args)
        except PodmanException as ex:
            raise PodmanException("Failed to run VLLM container.") from ex

    def list_containers(self, all_containers=True):
        """List containers.

        :param bool all_containers: If True, list all containers including stopped ones.
        :rtype: tuple with returncode, stdout (JSON list), stderr.
        """
        try:
            args = ["ps", "--format=json"]
            if all_containers:
                args.append("--all")
            return self.execute(*args)
        except PodmanException as ex:
            raise PodmanException("Failed to list containers.") from ex

    def logs(self, container_id, follow=False, tail=None):
        """Get container logs.

        :param str container_id: Container identification string.
        :param bool follow: If True, follow log output.
        :param int tail: Number of lines to show from the end of the logs.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["logs"]
            if follow:
                args.append("--follow")
            if tail is not None:
                args.extend(["--tail", str(tail)])
            args.append(container_id)
            return self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to get logs for container {container_id}."
            ) from ex

    def inspect(self, container_id):
        """Inspect a container and return detailed information.

        :param str container_id: Container identification string.
        :rtype: tuple with returncode, stdout (JSON), stderr.
        """
        try:
            return self.execute("inspect", container_id)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to inspect container {container_id}."
            ) from ex

    def remove(self, container_id, force=False):
        """Remove a container.

        :param str container_id: Container identification string.
        :param bool force: If True, force removal of running container.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["rm"]
            if force:
                args.append("--force")
            args.append(container_id)
            return self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(f"Failed to remove container {container_id}.") from ex

    def login(
        self,
        registry,
        username=None,
        password=None,
        api_key=None,
        api_key_username="iamapikey",
        password_stdin=False,
    ):
        """Login to a container registry.

        :param str registry: Registry URL.
        :param str username: Username for authentication (optional if using API key).
        :param str password: Password for authentication (optional if using API key).
        :param str api_key: API key for authentication (alternative to username/password).
        :param str api_key_username: Username to use with API key authentication (default: "iamapikey" for IBM Cloud).
                                     Other registries may use different conventions (e.g., "oauth2accesstoken" for GCR).
        :param bool password_stdin: If True, read password from stdin.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["login"]

            if api_key:
                args.extend(["--username", username or api_key_username])
                args.extend(["--password", api_key])
            elif username and password:
                args.extend(["--username", username])
                if not password_stdin:
                    args.extend(["--password", password])
            elif password_stdin:
                if username:
                    args.extend(["--username", username])
                args.append("--password-stdin")
            else:
                raise PodmanException(
                    "Must provide either api_key, username/password, or password_stdin"
                )

            args.append(registry)
            return self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(f"Failed to login to registry {registry}.") from ex

    def pull(self, image):
        """Pull an image from a registry.

        :param str image: Image name to pull.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            return self.execute("pull", image)
        except PodmanException as ex:
            raise PodmanException(f"Failed to pull image {image}.") from ex

    def stats(self, container_id, no_stream=True):
        """Get container resource usage statistics.

        :param str container_id: Container identification string.
        :param bool no_stream: If True, output stats once and exit.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["stats"]
            if no_stream:
                args.append("--no-stream")
            args.append(container_id)
            return self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to get stats for container {container_id}."
            ) from ex

    def get_container_port(self, container_id, port=8000, user=None):
        """
        Get the actual host port mapped to a container port.

        :param container_id: Container ID
        :param port: Container port to check (default: 8000)
        :param user: Username if container was created by specific user
        :return: Host port number or None
        """
        return get_container_port(container_id, port, user, LOG)

    def save_container_logs(self, container_id, log_dir, test_name="test", user=None):
        """
        Save complete container logs to a file.

        :param container_id: Container ID
        :param log_dir: Directory to save logs
        :param test_name: Test name for log file naming (default: "test")
        :param user: Username if container was created by specific user
        :return: Path to saved log file or None
        """
        return save_container_logs(container_id, log_dir, test_name, user, LOG)



class AsyncPodman(_Podman):
    async def execute(self, *args):
        """Execute a command and return the returncode, stdout and stderr.

        :param args: Variable length argument list to be used as argument
                      during execution.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            LOG.debug("Executing %s", args)

            proc = await create_subprocess_exec(
                self.podman_bin,
                *args,
                stdout=asyncio_subprocess.PIPE,
                stderr=asyncio_subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            LOG.debug("Return code: %s", proc.returncode)
            LOG.debug("Stdout: %s", stdout.decode("utf-8", "replace"))
            LOG.debug("Stderr: %s", stderr.decode("utf-8", "replace"))
        except (FileNotFoundError, PermissionError) as ex:
            msg = "Could not execute the command."
            LOG.error("%s: %s", msg, str(ex))
            raise PodmanException(msg) from ex

        if proc.returncode:
            command_args = " ".join(args)
            msg = f'Failure from command "{self.podman_bin} {command_args}": returned code "{proc.returncode}" stderr: "{stderr}"'
            LOG.error(msg)
            raise PodmanException(msg)

        return proc.returncode, stdout, stderr

    async def copy_to_container(self, container_id, src, dst):
        """Copy artifacts from src to container:dst.

        This method allows copying the contents of src to the dst. Files will
        be copied from the local machine to the container. The "src" argument
        can be a file or a directory.

        :param str container_id: string with the container identification.
        :param str src: what file or directory you are trying to copy.
        :param str dst: the destination inside the container.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("cp", src, f"{container_id}:{dst}")
        except PodmanException as ex:
            error = f"Failed copying data to container {container_id}"
            LOG.error(error)
            raise PodmanException(error) from ex

    async def get_python_version(self, image):
        """Return the current Python version installed in an image.

        :param str image: Image name. i.e: 'fedora:33'.
        :rtype: tuple with both: major, minor numbers and executable path.
        """
        try:
            _, stdout, _ = await self.execute(
                "run", "--rm", f"--entrypoint={self.PYTHON_VERSION_COMMAND}", image
            )
        except PodmanException as ex:
            raise PodmanException("Failed getting Python version.") from ex

        if stdout:
            output = stdout.decode().strip().split()
            return int(output[0]), int(output[1]), output[2]

    async def get_container_info(self, container_id):
        """Return all information about specific container.

        :param container_id: identifier of container
        :type container_id: str
        :rtype: dict
        """
        try:
            _, stdout, _ = await self.execute(
                "ps", "--all", "--format=json", "--filter", f"id={container_id}"
            )
        except PodmanException as ex:
            raise PodmanException(
                f"Failed getting information about container:" f" {container_id}."
            ) from ex
        containers = json.loads(stdout.decode())
        for container in containers:
            if container["Id"] == container_id:
                return container
        return {}

    async def start(self, container_id):
        """Starts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to start.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("start", container_id)
        except PodmanException as ex:
            raise PodmanException("Failed to start the container.") from ex

    async def stop(self, container_id):
        """Stops a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to stop.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("stop", "-t=0", container_id)
        except PodmanException as ex:
            raise PodmanException("Failed to stop the container.") from ex

    async def restart(self, container_id, timeout=10):
        """Restarts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to restart.
        :param int timeout: Timeout in seconds to wait for container to stop before killing it (default: 10).
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("restart", f"-t={timeout}", container_id)
        except PodmanException as ex:
            raise PodmanException("Failed to restart the container.") from ex

    async def exec_command(
        self,
        container_id,
        command,
        user=None,
        workdir=None,
        env=None,
        interactive=False,
        tty=False,
    ):
        """Execute a command in a running container.

        :param str container_id: Container identification string.
        :param str or list command: Command to execute. Can be a string or list of arguments.
        :param str user: Optional user to run the command as (e.g., "root", "1000", "1000:1000").
        :param str workdir: Optional working directory for the command.
        :param dict env: Optional dictionary of environment variables to set.
        :param bool interactive: Keep STDIN open even if not attached (default: False).
        :param bool tty: Allocate a pseudo-TTY (default: False).
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            cmd_args = ["exec"]

            # Add optional flags
            if interactive:
                cmd_args.append("-i")
            if tty:
                cmd_args.append("-t")
            if user is not None:
                cmd_args.extend(["-u", user])
            if workdir is not None:
                cmd_args.extend(["-w", workdir])
            if env is not None:
                for key, value in env.items():
                    cmd_args.extend(["-e", f"{key}={value}"])

            # Add container ID
            cmd_args.append(container_id)

            # Add command
            if isinstance(command, str):
                # If command is a string, split it for proper execution
                cmd_args.extend(command.split())
            elif isinstance(command, list):
                cmd_args.extend(command)
            else:
                raise PodmanException("Command must be a string or list")

            return await self.execute(*cmd_args)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to execute command in container {container_id}."
            ) from ex

    async def collect_container_aiu_metrics(
        self,
        container_id,
        output_file,
        dtcompiler_export_dir=None,
        stats_command="aiu-smi --csv",
        timeout=None,
    ):
        """
        Start collecting AIU metrics from a container in the background using nohup.

        This method runs a podman exec command in the background to continuously
        collect AIU metrics from a running container.

        :param str container_id: Container identification string.
        :param str output_file: Path to output file where stats will be saved (e.g., /path/to/aiu_metrics.csv).
        :param str dtcompiler_export_dir: Optional DTCOMPILER_EXPORT_DIR environment variable value.
        :param str stats_command: Command to run inside container for collecting stats
                                  (default: "aiu-smi --csv").
        :param int timeout: Optional timeout in seconds. If specified, stats collection will automatically
                           stop after this duration. If None, collection runs indefinitely.
        :return: Process object for the background process.
        :rtype: subprocess.Popen
        """
        try:
            # Build the podman exec command
            podman_cmd = [self.podman_bin, "exec"]

            # Add environment variable if provided
            if dtcompiler_export_dir:
                podman_cmd.extend(
                    ["-e", f"DTCOMPILER_EXPORT_DIR={dtcompiler_export_dir}"]
                )

            # Add container ID
            podman_cmd.append(container_id)

            # Add the bash command to execute
            podman_cmd.extend(["bash", "--login", "-c", stats_command])

            # Build the full command with optional timeout
            if timeout:
                # Use timeout command to automatically stop after specified duration
                full_command = f"nohup bash -c 'timeout {timeout} {' '.join(podman_cmd)} | tee {output_file}' > /dev/null 2>&1 &"
                LOG.info(
                    "Starting background stats collection with %d second timeout: %s",
                    timeout,
                    full_command,
                )
            else:
                # Run indefinitely without timeout
                full_command = f"nohup bash -c '{' '.join(podman_cmd)} | tee {output_file}' > /dev/null 2>&1 &"
                LOG.info(
                    "Starting background stats collection (no timeout): %s",
                    full_command,
                )

            # Execute the command in the background
            process = subprocess.Popen(
                full_command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

            LOG.info("Background stats collection started with PID: %s", process.pid)
            return process

        except Exception as ex:
            error_msg = f"Failed to start background stats collection for container {container_id}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    async def collect_container_stats(
        self, container_id, output_dir, interval=1, duration=60
    ):
        """
        Collect Podman CPU and memory stats and write as JSON.

        This method periodically collects container statistics (CPU and memory usage)
        and saves them to a JSON file for analysis. Supports collecting stats for a
        specific container or all running containers.

        :param str container_id: Container identification string or "all" for all containers.
        :param str output_dir: Base directory where stats JSON files will be saved.
                              Container-specific subdirectories will be created.
        :param int interval: Interval in seconds between stat collections (default: 1).
        :param int duration: Total duration in seconds to collect stats (default: 60).
        :return: Path to the generated JSON stats file (or list of paths if container_id="all").
        :rtype: str or list
        """
        try:
            # Determine which containers to monitor
            if container_id.lower() == "all":
                # Get all running containers
                _, stdout, _ = await self.execute("ps", "--format", "{{.ID}}")
                container_ids = stdout.decode().strip().split("\n")
                container_ids = [cid.strip() for cid in container_ids if cid.strip()]

                if not container_ids:
                    LOG.warning("No running containers found")
                    return []

                LOG.info("Collecting stats for %d containers", len(container_ids))

                # Collect stats for each container
                json_files = []
                for cid in container_ids:
                    json_file = await self._collect_single_container_stats(
                        cid, output_dir, interval, duration
                    )
                    json_files.append(json_file)

                return json_files
            else:
                # Collect stats for single container
                return await self._collect_single_container_stats(
                    container_id, output_dir, interval, duration
                )

        except Exception as ex:
            error_msg = f"Failed to collect stats for container(s): {container_id}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    async def _collect_single_container_stats(
        self, container_id, base_output_dir, interval, duration
    ):
        """
        Internal method to collect stats for a single container.

        :param str container_id: Container identification string.
        :param str base_output_dir: Base directory for output.
        :param int interval: Interval between collections.
        :param int duration: Total duration.
        :return: Path to JSON stats file.
        :rtype: str
        """
        try:
            # Create container-specific output directory
            container_output_dir = os.path.join(base_output_dir, container_id)
            Path(container_output_dir).mkdir(parents=True, exist_ok=True)
            json_file = os.path.join(container_output_dir, f"{container_id}_stats.json")

            all_stats = []
            end_time = time.time() + duration

            LOG.info(
                "Starting stats collection for container %s (duration: %ds, interval: %ds)",
                container_id,
                duration,
                interval,
            )

            while time.time() < end_time:
                try:
                    # Get stats using podman stats command
                    _, stdout, stderr = await self.execute(
                        "stats", "--no-stream", "--format", "json", container_id
                    )

                    if stderr:
                        LOG.warning(
                            "[%s] stderr: %s", container_id, stderr.decode().strip()
                        )
                        await asyncio.sleep(interval)
                        continue

                    # Parse JSON stats
                    stats_list = json.loads(stdout.decode())
                    if stats_list:
                        stats = stats_list[0]
                        entry = {
                            "timestamp": datetime.datetime.utcnow().isoformat(),
                            "cpu_percent": stats.get("cpu_percent", ""),
                            "mem_percent": stats.get("mem_percent", ""),
                            "mem_usage": stats.get("mem_usage", ""),
                            "net_io": stats.get("net_io", ""),
                            "block_io": stats.get("block_io", ""),
                            "pids": stats.get("pids", ""),
                        }
                        all_stats.append(entry)
                        LOG.debug(
                            "[%s] CPU: %s%%, MEM: %s%%",
                            container_id,
                            entry["cpu_percent"],
                            entry["mem_percent"],
                        )

                except json.JSONDecodeError as je:
                    LOG.error("[%s] Failed to parse stats JSON: %s", container_id, je)
                except PodmanException as pe:
                    LOG.error("[%s] Failed to get stats: %s", container_id, pe)

                await asyncio.sleep(interval)

            # Write all stats to JSON file
            with open(json_file, "w", encoding="utf-8") as jf:
                json.dump(all_stats, jf, indent=2)

            LOG.info(
                "[%s] Collected %d stat entries → %s",
                container_id,
                len(all_stats),
                json_file,
            )
            return json_file

        except Exception as ex:
            error_msg = f"Failed to collect stats for container {container_id}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    async def send_vllm_inference_request(
        self,
        port,
        model_path,
        prompt,
        max_tokens=512,
        temperature=1.0,
        system_message="You are a helpful AI assistant.",
        host="127.0.0.1",
        use_jq=True,
    ):
        """
        Send an inference request to VLLM server using curl.

        This method sends a chat completion request to a running VLLM container
        and returns the response.

        :param int port: Port number where VLLM server is listening.
        :param str model_path: Model path as configured in VLLM (e.g., "/models/granite-3.3-8b-instruct").
        :param str prompt: User prompt/query to send to the model.
        :param int max_tokens: Maximum number of tokens to generate (default: 512).
        :param float temperature: Sampling temperature (default: 1.0).
        :param str system_message: System message to set context (default: "You are a helpful AI assistant.").
        :param str host: Host address (default: "127.0.0.1").
        :param bool use_jq: Whether to pipe output through jq for formatting (default: True).
        :return: Tuple of (returncode, response_text, error_text).
        :rtype: tuple
        """
        try:
            # Build the JSON payload
            payload = {
                "model": model_path,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
            }

            # Convert payload to JSON string
            payload_json = json.dumps(payload)

            # Build the curl command
            url = f"http://{host}:{port}/v1/chat/completions"

            curl_cmd = [
                "curl",
                url,
                "-H",
                "Content-Type: application/json",
                "-d",
                payload_json,
            ]

            # Add jq for pretty printing if requested
            if use_jq:
                curl_cmd_str = " ".join(
                    [f"'{arg}'" if " " in arg else arg for arg in curl_cmd]
                )
                full_cmd_str = f"{curl_cmd_str} | jq"
                LOG.info("Sending inference request: %s", full_cmd_str)

                # Execute with shell for piping to jq
                proc = await asyncio.create_subprocess_shell(
                    full_cmd_str,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                LOG.info("Sending inference request to %s", url)

                # Execute directly without shell
                proc = await asyncio.create_subprocess_exec(
                    *curl_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
                returncode = proc.returncode

                if returncode == 0:
                    LOG.info("Inference request successful")
                    LOG.debug(
                        "Response: %s", stdout.decode()[:500]
                    )  # Log first 500 chars
                else:
                    LOG.error("Inference request failed with code %d", returncode)
                    LOG.error("Error: %s", stderr.decode())

                return returncode, stdout.decode(), stderr.decode()

            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                error_msg = "Inference request timed out after 300 seconds"
                LOG.error(error_msg)
                raise PodmanException(error_msg)

        except Exception as ex:
            error_msg = f"Failed to send inference request to {host}:{port}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    async def run_vllm_container(
        self,
        image,
        aiu_ids,
        host_models_dir,
        vllm_model_path,
        aiu_world_size,
        max_model_len,
        max_batch_size,
        memory="100G",
        shm_size="2G",
        device="/dev/vfio",
        privileged="true",
        pids_limit="0",
        userns="keep-id",
        group_add="keep-groups",
        port_mapping="127.0.0.1::8000",
        vllm_spyre_use_cb="1",
        vllm_dt_chunk_len=None,
        vllm_spyre_use_chunked_prefill=None,
        enable_prefix_caching=True,
        additional_vllm_args=None,
        container_name=None,
    ):
        """Run a VLLM container with AIU support.

        :param str image: Container image to run.
        :param str aiu_ids: Space-separated AIU PCIe IDs.
        :param str host_models_dir: Host directory containing models.
        :param str vllm_model_path: Path to model inside container.
        :param int aiu_world_size: AIU world size (tensor parallelism).
        :param int max_model_len: Maximum model length.
        :param int max_batch_size: Maximum batch size.
        :param str memory: Memory limit (default: "100G" - adjust based on model size).
        :param str shm_size: Shared memory size (default: "2G" - increase for larger batches).
        :param str device: Device to mount (default: "/dev/vfio").
        :param str privileged: Run in privileged mode (default: "true").
        :param str pids_limit: PIDs limit (default: "0" - unlimited).
        :param str userns: User namespace mode (default: "keep-id").
        :param str group_add: Group add mode (default: "keep-groups").
        :param str port_mapping: Port mapping in format
            ``[host_ip]:[host_port]:container_port`` (default:
            ``"127.0.0.1::8000"`` - localhost with random host port to
            container port 8000). Examples:
            ``"127.0.0.1:8000:8000"`` (fixed host port 8000),
            ``"0.0.0.0::8000"`` (all interfaces, random host port),
            ``"::8000"`` (all interfaces, random host port).
        :param str vllm_spyre_use_cb: Use CB flag (default: "1").
        :param int vllm_dt_chunk_len: Optional DT chunk length.
        :param int vllm_spyre_use_chunked_prefill: Optional chunked prefill flag.
        :param bool enable_prefix_caching: Enable VLLM prefix caching (default: True).
        :param list additional_vllm_args: Additional VLLM command-line arguments as list of strings.
        :param str container_name: Optional container name.
        :rtype: tuple with returncode, stdout (container ID), stderr.
        """
        cmd_args = [
            "run",
            "-d",
            "-it",
            f"--device={device}",
            "-v",
            f"{host_models_dir}:/models",
            "-e",
            f"AIU_PCIE_IDS={aiu_ids}",
            "-e",
            f"VLLM_SPYRE_USE_CB={vllm_spyre_use_cb}",
            f"--privileged={privileged}",
            "--pids-limit",
            pids_limit,
            f"--userns={userns}",
            f"--group-add={group_add}",
            "--memory",
            memory,
            "--shm-size",
            shm_size,
            "-p",
            port_mapping,
        ]

        if vllm_dt_chunk_len is not None:
            cmd_args.extend(["-e", f"VLLM_DT_CHUNK_LEN={vllm_dt_chunk_len}"])
        if vllm_spyre_use_chunked_prefill is not None:
            cmd_args.extend(
                [
                    "-e",
                    f"VLLM_SPYRE_USE_CHUNKED_PREFILL={vllm_spyre_use_chunked_prefill}",
                ]
            )

        if container_name:
            cmd_args.extend(["--name", container_name])

        cmd_args.extend(
            [
                image,
                "--model",
                vllm_model_path,
                "-tp",
                str(aiu_world_size),
                "--max-model-len",
                str(max_model_len),
                "--max-num-seqs",
                str(max_batch_size),
            ]
        )

        if enable_prefix_caching:
            cmd_args.append("--enable-prefix-caching")

        if additional_vllm_args:
            if isinstance(additional_vllm_args, list):
                cmd_args.extend(additional_vllm_args)
            else:
                raise PodmanException(
                    f"additional_vllm_args must be a list, got {type(additional_vllm_args).__name__}"
                )

        try:
            return await self.execute(*cmd_args)
        except PodmanException as ex:
            raise PodmanException("Failed to run VLLM container.") from ex

    async def list_containers(self, all_containers=True):
        """List containers.

        :param bool all_containers: If True, list all containers including stopped ones.
        :rtype: tuple with returncode, stdout (JSON list), stderr.
        """
        try:
            args = ["ps", "--format=json"]
            if all_containers:
                args.append("--all")
            return await self.execute(*args)
        except PodmanException as ex:
            raise PodmanException("Failed to list containers.") from ex

    async def logs(self, container_id, follow=False, tail=None):
        """Get container logs.

        :param str container_id: Container identification string.
        :param bool follow: If True, follow log output.
        :param int tail: Number of lines to show from the end of the logs.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["logs"]
            if follow:
                args.append("--follow")
            if tail is not None:
                args.extend(["--tail", str(tail)])
            args.append(container_id)
            return await self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to get logs for container {container_id}."
            ) from ex

    async def inspect(self, container_id):
        """Inspect a container and return detailed information.

        :param str container_id: Container identification string.
        :rtype: tuple with returncode, stdout (JSON), stderr.
        """
        try:
            return await self.execute("inspect", container_id)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to inspect container {container_id}."
            ) from ex

    async def remove(self, container_id, force=False):
        """Remove a container.

        :param str container_id: Container identification string.
        :param bool force: If True, force removal of running container.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["rm"]
            if force:
                args.append("--force")
            args.append(container_id)
            return await self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(f"Failed to remove container {container_id}.") from ex

    async def login(
        self,
        registry,
        username=None,
        password=None,
        api_key=None,
        api_key_username="iamapikey",
        password_stdin=False,
    ):
        """Login to a container registry.

        :param str registry: Registry URL.
        :param str username: Username for authentication (optional if using API key).
        :param str password: Password for authentication (optional if using API key).
        :param str api_key: API key for authentication (alternative to username/password).
        :param str api_key_username: Username to use with API key authentication (default: "iamapikey" for IBM Cloud).
                                     Other registries may use different conventions (e.g., "oauth2accesstoken" for GCR).
        :param bool password_stdin: If True, read password from stdin.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["login"]

            if api_key:
                args.extend(["--username", username or api_key_username])
                args.extend(["--password", api_key])
            elif username and password:
                args.extend(["--username", username])
                if not password_stdin:
                    args.extend(["--password", password])
            elif password_stdin:
                if username:
                    args.extend(["--username", username])
                args.append("--password-stdin")
            else:
                raise PodmanException(
                    "Must provide either api_key, username/password, or password_stdin"
                )

            args.append(registry)
            return await self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(f"Failed to login to registry {registry}.") from ex

    async def pull(self, image):
        """Pull an image from a registry.

        :param str image: Image name to pull.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            return await self.execute("pull", image)
        except PodmanException as ex:
            raise PodmanException(f"Failed to pull image {image}.") from ex

    async def stats(self, container_id, no_stream=True):
        """Get container resource usage statistics.

        :param str container_id: Container identification string.
        :param bool no_stream: If True, output stats once and exit.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["stats"]
            if no_stream:
                args.append("--no-stream")
            args.append(container_id)
            return await self.execute(*args)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to get stats for container {container_id}."
            ) from ex

    async def get_container_port(self, container_id, port=8000, user=None):
        """
        Get the actual host port mapped to a container port.

        :param container_id: Container ID
        :param port: Container port to check (default: 8000)
        :param user: Username if container was created by specific user
        :return: Host port number or None
        """
        return get_container_port(container_id, port, user, LOG)

    async def save_container_logs(self, container_id, log_dir, test_name="test", user=None):
        """
        Save complete container logs to a file.

        :param container_id: Container ID
        :param log_dir: Directory to save logs
        :param test_name: Test name for log file naming (default: "test")
        :param user: Username if container was created by specific user
        :return: Path to saved log file or None
        """
        return save_container_logs(container_id, log_dir, test_name, user, LOG)


    async def run_multiple_vllm_containers(
        self,
        num_containers,
        image,
        aiu_ids_list,
        host_models_dir,
        vllm_model_path,
        aiu_world_size,
        max_model_len,
        max_batch_size,
        memory="100G",
        shm_size="2G",
        device="/dev/vfio",
        privileged="true",
        pids_limit="0",
        userns="keep-id",
        group_add="keep-groups",
        port_mapping="127.0.0.1::8000",
        vllm_spyre_use_cb="1",
        vllm_dt_chunk_len=None,
        vllm_spyre_use_chunked_prefill=None,
        enable_prefix_caching=True,
        additional_vllm_args=None,
        container_name_prefix="vllm-container",
    ):
        """Run multiple VLLM containers concurrently with different AIU IDs.

        :param int num_containers: Number of containers to create.
        :param str image: Container image to run.
        :param list aiu_ids_list: List of AIU PCIe IDs for each container.
                                  Must provide exactly num_containers AIU ID sets.
        :param str host_models_dir: Host directory containing models.
        :param str vllm_model_path: Path to model inside container.
        :param int aiu_world_size: AIU world size (tensor parallelism).
        :param int max_model_len: Maximum model length.
        :param int max_batch_size: Maximum batch size.
        :param str memory: Memory limit (default: "100G").
        :param str shm_size: Shared memory size (default: "2G").
        :param str device: Device to mount (default: "/dev/vfio").
        :param str privileged: Run in privileged mode (default: "true").
        :param str pids_limit: PIDs limit (default: "0").
        :param str userns: User namespace mode (default: "keep-id").
        :param str group_add: Group add mode (default: "keep-groups").
        :param str port_mapping: Port mapping (default: "127.0.0.1::8000").
        :param str vllm_spyre_use_cb: Use CB flag (default: "1").
        :param int vllm_dt_chunk_len: Optional DT chunk length.
        :param int vllm_spyre_use_chunked_prefill: Optional chunked prefill flag.
        :param bool enable_prefix_caching: Enable VLLM prefix caching (default: True).
        :param list additional_vllm_args: Additional VLLM command-line arguments as list of strings.
        :param str container_name_prefix: Prefix for container names.
        :rtype: list of tuples (container_name, returncode, stdout, stderr).
        """
        if not isinstance(aiu_ids_list, list):
            raise PodmanException(
                f"aiu_ids_list must be a list, got {type(aiu_ids_list).__name__}"
            )

        if len(aiu_ids_list) != num_containers:
            raise PodmanException(
                f"Number of AIU ID sets ({len(aiu_ids_list)}) must match "
                f"number of containers ({num_containers}). "
                f"Each container requires its own unique AIU IDs."
            )

        container_names = []
        tasks = []
        for i in range(num_containers):
            container_name = f"{container_name_prefix}-{i}"
            container_names.append(container_name)
            task = self.run_vllm_container(
                image=image,
                aiu_ids=aiu_ids_list[i],
                host_models_dir=host_models_dir,
                vllm_model_path=vllm_model_path,
                aiu_world_size=aiu_world_size,
                max_model_len=max_model_len,
                max_batch_size=max_batch_size,
                memory=memory,
                shm_size=shm_size,
                device=device,
                privileged=privileged,
                pids_limit=pids_limit,
                userns=userns,
                group_add=group_add,
                port_mapping=port_mapping,
                vllm_spyre_use_cb=vllm_spyre_use_cb,
                vllm_dt_chunk_len=vllm_dt_chunk_len,
                vllm_spyre_use_chunked_prefill=vllm_spyre_use_chunked_prefill,
                enable_prefix_caching=enable_prefix_caching,
                additional_vllm_args=additional_vllm_args,
                container_name=container_name,
            )
            tasks.append(task)

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        for container_name, result in zip(container_names, task_results):
            if isinstance(result, Exception):
                LOG.error(
                    "Failed to create container %s: %s", container_name, str(result)
                )
                results.append((container_name, None, None, str(result)))
            elif isinstance(result, tuple) and len(result) == 3:
                returncode, stdout, stderr = result
                results.append((container_name, returncode, stdout, stderr))
                LOG.info("Container %s created successfully", container_name)
            else:
                LOG.error(
                    "Unexpected result type for container %s: %s",
                    container_name,
                    type(result),
                )
                results.append((container_name, None, None, "Unexpected result type"))

        return results

    async def start_multiple_containers(self, container_ids):
        """Start multiple containers concurrently.

        :param list container_ids: List of container IDs to start.
        :rtype: list of tuples (container_id, returncode, stdout, stderr).
        """
        tasks = [self.start(container_id) for container_id in container_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for container_id, result in zip(container_ids, results):
            if isinstance(result, Exception):
                LOG.error("Failed to start container %s: %s", container_id, str(result))
                output.append((container_id, None, None, str(result)))
            elif isinstance(result, tuple) and len(result) == 3:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))
                LOG.info("Container %s started successfully", container_id)
            else:
                LOG.error(
                    "Unexpected result type for container %s: %s",
                    container_id,
                    type(result),
                )
                output.append((container_id, None, None, "Unexpected result type"))

        return output

    async def stop_multiple_containers(self, container_ids):
        """Stop multiple containers concurrently.

        :param list container_ids: List of container IDs to stop.
        :rtype: list of tuples (container_id, returncode, stdout, stderr).
        """
        tasks = [self.stop(container_id) for container_id in container_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for container_id, result in zip(container_ids, results):
            if isinstance(result, Exception):
                LOG.error("Failed to stop container %s: %s", container_id, str(result))
                output.append((container_id, None, None, str(result)))
            elif isinstance(result, tuple) and len(result) == 3:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))
                LOG.info("Container %s stopped successfully", container_id)
            else:
                LOG.error(
                    "Unexpected result type for container %s: %s",
                    container_id,
                    type(result),
                )
                output.append((container_id, None, None, "Unexpected result type"))

        return output

    async def remove_multiple_containers(self, container_ids, force=False):
        """Remove multiple containers concurrently.

        :param list container_ids: List of container IDs to remove.
        :param bool force: If True, force removal of running containers.
        :rtype: list of tuples (container_id, returncode, stdout, stderr).
        """
        tasks = [
            self.remove(container_id, force=force) for container_id in container_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for container_id, result in zip(container_ids, results):
            if isinstance(result, Exception):
                LOG.error(
                    "Failed to remove container %s: %s", container_id, str(result)
                )
                output.append((container_id, None, None, str(result)))
            elif isinstance(result, tuple) and len(result) == 3:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))
                LOG.info("Container %s removed successfully", container_id)
            else:
                LOG.error(
                    "Unexpected result type for container %s: %s",
                    container_id,
                    type(result),
                )
                output.append((container_id, None, None, "Unexpected result type"))

        return output

    async def get_multiple_container_logs(self, container_ids, tail=None):
        """Get logs from multiple containers concurrently.

        :param list container_ids: List of container IDs.
        :param int tail: Number of lines to show from the end of the logs.
        :rtype: list of tuples (container_id, returncode, stdout, stderr).
        """
        tasks = [self.logs(container_id, tail=tail) for container_id in container_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for container_id, result in zip(container_ids, results):
            if isinstance(result, Exception):
                LOG.error(
                    "Failed to get logs for container %s: %s", container_id, str(result)
                )
                output.append((container_id, None, None, str(result)))
            elif isinstance(result, tuple) and len(result) == 3:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))
            else:
                LOG.error(
                    "Unexpected result type for container %s: %s",
                    container_id,
                    type(result),
                )
                output.append((container_id, None, None, "Unexpected result type"))

        return output

