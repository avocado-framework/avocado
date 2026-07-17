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
import shlex
import subprocess
import time
from asyncio import create_subprocess_exec
from asyncio import subprocess as asyncio_subprocess
from pathlib import Path
from shutil import which

LOG = logging.getLogger(__name__)


def setup_user_and_group(username, password, spyre_group, add_to_group=True, log=None):
    """
    Setup user and manage group membership for non-root container execution.

    :param username: Username to setup (None or "root" for root user)
    :param password: Password for user (not used for root)
    :param spyre_group: Group name to add/remove user to/from (e.g., "spyre_group")
    :param add_to_group: True to add user to group, False to remove (default: True)
    :param log: Logger instance (optional)
    :return: None
    """
    if log is None:
        log = LOG

    if username is None or username == "root":
        if spyre_group:
            if add_to_group:
                log.info("Add root user to %s group", spyre_group)
                subprocess.run(["usermod", "-aG", spyre_group, "root"], check=False)
            else:
                log.info("Remove root user from %s group", spyre_group)
                subprocess.run(["gpasswd", "-d", "root", spyre_group], check=False)
    else:
        # Check if user exists
        user_check = subprocess.run(
            ["id", "-u", username], capture_output=True, check=False
        )

        if user_check.returncode != 0:
            log.info("Create user: %s", username)
            subprocess.run(["useradd", "-m", username], check=False)
            # Use input parameter to pass password securely to chpasswd
            subprocess.run(
                ["chpasswd"], input=f"{username}:{password}\n".encode(), check=False
            )

        if spyre_group:
            if add_to_group:
                log.info("Add %s to %s group", username, spyre_group)
                subprocess.run(["usermod", "-aG", spyre_group, username], check=False)
            else:
                log.info("Remove %s from %s group", username, spyre_group)
                subprocess.run(["gpasswd", "-d", username, spyre_group], check=False)


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
            # Get user ID first
            id_result = subprocess.run(
                ["id", "-u", user], capture_output=True, text=True, check=False
            )
            if id_result.returncode != 0:
                log.error("Failed to get user ID for %s", user)
                return None
            user_id = id_result.stdout.strip()
            xdg_runtime_dir = f"/run/user/{user_id}"
            # Run podman port command as user with proper environment
            result = subprocess.run(
                [
                    "su",
                    "-",
                    user,
                    "-c",
                    f"XDG_RUNTIME_DIR={xdg_runtime_dir} podman port {container_id} {port}",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        else:
            result = subprocess.run(
                ["podman", "port", container_id, str(port)],
                capture_output=True,
                text=True,
                check=False,
            )

        if result.returncode == 0:
            port_output = result.stdout.strip()
            log.info("Port mapping output: %s", port_output)

            if port_output and ":" in port_output:
                host_port = port_output.strip().split(":")[-1]
                log.info(
                    "Container port %d is mapped to host port: %s", port, host_port
                )
                return int(host_port)
            else:
                log.warning("Could not parse port from output: %s", port_output)
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
            # Get user ID first
            id_result = subprocess.run(
                ["id", "-u", user], capture_output=True, text=True, check=False
            )
            if id_result.returncode != 0:
                log.error("Failed to get user ID for %s", user)
                return None
            user_id = id_result.stdout.strip()
            xdg_runtime_dir = f"/run/user/{user_id}"
            # Run podman logs command as user with proper environment
            result = subprocess.run(
                [
                    "su",
                    "-",
                    user,
                    "-c",
                    f"XDG_RUNTIME_DIR={xdg_runtime_dir} podman logs {container_id}",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        else:
            result = subprocess.run(
                ["podman", "logs", container_id],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

        if result.returncode == 0:
            log_content = result.stdout
        else:
            log_content = f"Error retrieving logs:\n{result.stderr}\n\nPartial stdout:\n{result.stdout}"

        # Save logs to file
        with open(log_filepath, "w", encoding="utf-8") as f:
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


def wait_for_vllm_startup(
    container_id,
    success_pattern="Application startup complete.",
    failure_pattern=None,
    additional_failure_checks=None,
    timeout=300,
    check_interval=20,
    user=None,
    log=None,
    show_live_logs=True,
    live_log_lines=20,
):
    """
    Wait for container to start by checking logs for a success pattern.

    This is a generic function that can be used for any container type.
    The success and failure patterns can be customized based on the application.

    :param container_id: Container ID to monitor
    :param success_pattern: String pattern to look for in logs indicating successful startup
    :param failure_pattern: Optional string pattern indicating startup failure (e.g., "BACKTRACE")
    :param additional_failure_checks: Optional list of tuples [(pattern, case_sensitive), ...]
                                     for additional failure detection. Example:
                                     [("VFIO", False), ("fail", False)] checks for "VFIO" and "fail"
    :param timeout: Maximum time to wait in seconds (default: 300)
    :param check_interval: Time between log checks in seconds (default: 10)
    :param user: Username if container was created by specific user
    :param log: Logger instance (optional)
    :param show_live_logs: If True, display recent log lines during each check (default: True)
    :param live_log_lines: Number of recent log lines to display (default: 10)
    :return: True if startup successful, False otherwise
    """
    if log is None:
        log = LOG

    elapsed = 0
    last_log_position = 0

    while elapsed < timeout:
        try:
            # Get container logs directly using capture_output
            if user and user != "root":
                # Get user ID first
                id_result = subprocess.run(
                    ["id", "-u", user], capture_output=True, text=True, check=False
                )
                if id_result.returncode != 0:
                    log.warning("Failed to get user ID for %s", user)
                    time.sleep(check_interval)
                    elapsed += check_interval
                    continue
                user_id = id_result.stdout.strip()
                xdg_runtime_dir = f"/run/user/{user_id}"
                # Run podman logs command as user with proper environment
                result = subprocess.run(
                    [
                        "su",
                        "-",
                        user,
                        "-c",
                        f"XDG_RUNTIME_DIR={xdg_runtime_dir} podman logs {container_id}",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
            else:
                # For root user, run directly
                result = subprocess.run(
                    ["podman", "logs", container_id],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
            # Combine stdout and stderr
            log_content = result.stdout + result.stderr
            if show_live_logs and log_content:
                log_lines = log_content.split("\n")
                current_log_length = len(log_lines)
                if current_log_length > last_log_position:
                    new_lines = log_lines[last_log_position:]
                    display_lines = (
                        new_lines[-live_log_lines:]
                        if len(new_lines) > live_log_lines
                        else new_lines
                    )
                    if display_lines:
                        log.info("=== Recent Container Logs ===")
                        for line in display_lines:
                            if line.strip():  # Only show non-empty lines
                                log.info("  %s", line)
                        log.info("=== End Logs ===")
                    last_log_position = current_log_length
            if failure_pattern and failure_pattern in log_content:
                log.error(
                    "%s detected in container logs - startup failed", failure_pattern
                )
                log.error("Container logs:\n%s", log_content)
                return False
            if additional_failure_checks:
                for pattern, case_sensitive in additional_failure_checks:
                    check_content = (
                        log_content if case_sensitive else log_content.lower()
                    )
                    check_pattern = pattern if case_sensitive else pattern.lower()
                    if check_pattern in check_content:
                        log.error("Failure pattern '%s' detected in logs", pattern)
                        log.error("Container logs:\n%s", log_content)
                        return False
            if success_pattern in log_content:
                log.info("✓ Container started successfully: %s", container_id)
                return True
            log.info(
                "Waiting for container startup... (%d/%d seconds)", elapsed, timeout
            )
            time.sleep(check_interval)
            elapsed += check_interval

        except subprocess.TimeoutExpired:
            log.warning("Timeout getting container logs")
            time.sleep(check_interval)
            elapsed += check_interval
        except Exception as ex:
            log.warning("Failed to get container logs: %s", ex)
            time.sleep(check_interval)
            elapsed += check_interval

    log.error("Timeout waiting for container startup")
    return False


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
                    timeout=10,
                )
                if result.returncode == 0:
                    LOG.info("Hugging Face CLI version: %s", result.stdout.strip())
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
            timeout=300,
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
                    "/usr/bin/hf",
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
    import glob
    import hashlib

    validation_messages = []
    is_valid = True
    required_files = ["config.json", "tokenizer.json", "tokenizer_config.json"]
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
                f"OK: {req_file} ({os.path.getsize(file_path)} bytes)"
            )
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
                validation_messages.append(f"EMPTY: {os.path.basename(weight_file)}")
                is_valid = False
            else:
                validation_messages.append(
                    f"OK: {os.path.basename(weight_file)} ({file_size} bytes)"
                )
    sha_file = os.path.join(model_path, "SHA256SUMS")

    if os.path.exists(sha_file):
        validation_messages.append(f"Found checksum file: {os.path.basename(sha_file)}")
        try:
            with open(sha_file, "r", encoding="utf-8") as f:
                sha_content = f.read()
            for weight_file in weight_files:
                filename = os.path.basename(weight_file)
                if filename in sha_content:
                    validation_messages.append(f"Validating SHA256 for: {filename}")
                    sha256_hash = hashlib.sha256()
                    try:
                        with open(weight_file, "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                        actual_sha = sha256_hash.hexdigest()
                        if actual_sha[:16] in sha_content:
                            validation_messages.append(f"SHA256 VALID: {filename}")
                        else:
                            validation_messages.append(f"SHA256 MISMATCH: {filename}")
                            validation_messages.append(
                                f"  Calculated: {actual_sha[:16]}..."
                            )
                            is_valid = False
                    except Exception as sha_ex:
                        validation_messages.append(
                            f"SHA256 calculation failed for {filename}: {sha_ex}"
                        )
        except Exception as ex:
            validation_messages.append(f"Failed to read checksum file: {ex}")
    else:
        validation_messages.append("No checksum file found - skipping SHA validation")

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
    def execute(self, *args, user=None):
        """Execute a command and return the returncode, stdout and stderr.

        :param args: Variable length argument list to be used as argument
                      during execution.
        :param user: Optional user to run command as (uses 'su - user -c')
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            LOG.debug("Executing %s", args)

            if user:
                podman_cmd = [self.podman_bin] + list(args)
                podman_cmd_str = " ".join(shlex.quote(str(arg)) for arg in podman_cmd)
                cmd = ["su", "-", user, "-c", podman_cmd_str]
            else:
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
                    command_args = " ".join(str(a) for a in args)
                    msg = f'Failure from command "{self.podman_bin} {command_args}": returned code "{proc.returncode}" stderr: "{stderr}"'
                    LOG.error(msg)
                    raise PodmanException(msg)

                return proc.returncode, stdout, stderr
        except (FileNotFoundError, PermissionError) as ex:
            msg = "Could not execute the command."
            LOG.error("%s: %s", msg, str(ex))
            raise PodmanException(msg) from ex

    def copy_to_container(self, container_id, src, dst, user=None):
        """Copy artifacts from src to container:dst.

        This method allows copying the contents of src to the dst. Files will
        be copied from the local machine to the container. The "src" argument
        can be a file or a directory.

        :param str container_id: string with the container identification.
        :param str src: what file or directory you are trying to copy.
        :param str dst: the destination inside the container.
        :param str user: Optional user to run command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("cp", src, f"{container_id}:{dst}", user=user)
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

    def get_container_info(self, container_id, user=None):
        """Return all information about specific container.

        :param container_id: identifier of container
        :type container_id: str
        :param user: Optional user to run command as
        :type user: str
        :rtype: dict
        """
        try:
            _, stdout, _ = self.execute(
                "ps",
                "--all",
                "--format=json",
                "--filter",
                f"id={container_id}",
                user=user,
            )
        except PodmanException as ex:
            raise PodmanException(
                f"Failed getting information about container: {container_id}."
            ) from ex
        containers = json.loads(stdout.decode())
        # Return first container if found (filter by id should return only one)
        if containers and len(containers) > 0:
            return containers[0]
        return {}

    def start(self, container_id, user=None):
        """Starts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to start.
        :param str user: Optional user to run command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("start", container_id, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to start the container.") from ex

    def stop(self, container_id, user=None):
        """Stops a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to stop.
        :param str user: Optional user to run command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("stop", "-t=0", container_id, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to stop the container.") from ex

    def restart(self, container_id, timeout=10, user=None):
        """Restarts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to restart.
        :param int timeout: Timeout in seconds to wait for container to stop before killing it (default: 10).
        :param str user: Optional user to run command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return self.execute("restart", f"-t={timeout}", container_id, user=user)
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
        podman_user=None,
    ):
        """Execute a command in a running container.

        :param str container_id: Container identification string.
        :param str or list command: Command to execute. Can be a string or list of arguments.
        :param str user: Optional user to run the command as inside container (e.g., "root", "1000", "1000:1000").
        :param str workdir: Optional working directory for the command.
        :param dict env: Optional dictionary of environment variables to set.
        :param bool interactive: Keep STDIN open even if not attached (default: False).
        :param bool tty: Allocate a pseudo-TTY (default: False).
        :param str podman_user: Optional system user to run podman command as.
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

            return self.execute(*cmd_args, user=podman_user)
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
        user=None,
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
        :param str user: Optional system user to run podman command as.
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

            # Build the command string using shlex.join to properly quote arguments
            podman_cmd_str = shlex.join(podman_cmd)
            if timeout:
                base_command = f"timeout {timeout} {podman_cmd_str} | tee {output_file}"
            else:
                base_command = f"{podman_cmd_str} | tee {output_file}"
            # Wrap with user if specified
            if user:
                full_command = f"nohup su - {user} -c {shlex.quote(base_command)} > /dev/null 2>&1 &"
            else:
                full_command = (
                    f"nohup bash -c {shlex.quote(base_command)} > /dev/null 2>&1 &"
                )
            LOG.info("Starting background stats collection: %s", full_command)

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
        self, container_id, output_dir, interval=1, duration=60, user=None
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
        :param str user: Optional system user to run podman command as.
        :return: Path to the generated JSON stats file (or list of paths if container_id="all").
        :rtype: str or list
        """
        try:
            if container_id.lower() == "all":
                _, stdout, _ = self.execute("ps", "--format", "{{.ID}}", user=user)
                container_ids = stdout.decode().strip().split("\n")
                container_ids = [cid.strip() for cid in container_ids if cid.strip()]

                if not container_ids:
                    LOG.warning("No running containers found")
                    return []

                LOG.info("Collecting stats for %d containers", len(container_ids))

                json_files = []
                for cid in container_ids:
                    json_file = self._collect_single_container_stats(
                        cid, output_dir, interval, duration, user
                    )
                    json_files.append(json_file)

                return json_files
            else:
                return self._collect_single_container_stats(
                    container_id, output_dir, interval, duration, user
                )

        except Exception as ex:
            error_msg = f"Failed to collect stats for container(s): {container_id}"
            LOG.error("%s: %s", error_msg, ex)
            raise PodmanException(error_msg) from ex

    def _collect_single_container_stats(
        self, container_id, base_output_dir, interval, duration, user=None
    ):
        """
        Internal method to collect stats for a single container.

        :param str container_id: Container identification string.
        :param str base_output_dir: Base directory for output.
        :param int interval: Interval between collections.
        :param int duration: Total duration.
        :param str user: Optional system user to run podman command as.
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
                        "stats",
                        "--no-stream",
                        "--format",
                        "json",
                        container_id,
                        user=user,
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

    def run(self, podman_options=None, user=None):
        """
        Run a container with command-line arguments as a list.

        This is a simplified generic container runner that accepts a list
        of command-line arguments to pass to 'podman run'.

        :param list podman_options: List of command-line arguments for 'podman run'.
            Example: ["-d", "--name", "test", "-e", "VAR=value",
            "--memory", "100G", "image:tag", "--model", "/path"]
        :param str user: Optional user to run podman command as (uses 'su - user -c')
        :return: tuple (returncode, stdout, stderr)
        """
        if not podman_options:
            raise PodmanException("podman_options is required")

        if not isinstance(podman_options, list):
            raise PodmanException("podman_options must be a list of strings")

        cmd_args = ["run"] + podman_options

        try:
            return self.execute(*cmd_args, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to run container.") from ex

    def list_containers(self, all_containers=True, user=None):
        """List containers.

        :param bool all_containers: If True, list all containers including stopped ones.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout (JSON list), stderr.
        """
        try:
            args = ["ps", "--format=json"]
            if all_containers:
                args.append("--all")
            return self.execute(*args, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to list containers.") from ex

    def logs(self, container_id, follow=False, tail=None, user=None):
        """Get container logs.

        :param str container_id: Container identification string.
        :param bool follow: If True, follow log output.
        :param int tail: Number of lines to show from the end of the logs.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["logs"]
            if follow:
                args.append("--follow")
            if tail is not None:
                args.extend(["--tail", str(tail)])
            args.append(container_id)
            return self.execute(*args, user=user)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to get logs for container {container_id}."
            ) from ex

    def inspect(self, container_id, user=None):
        """Inspect a container and return detailed information.

        :param str container_id: Container identification string.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout (JSON), stderr.
        """
        try:
            return self.execute("inspect", container_id, user=user)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to inspect container {container_id}."
            ) from ex

    def remove(self, container_id, force=False, user=None):
        """Remove a container.

        :param str container_id: Container identification string.
        :param bool force: If True, force removal of running container.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["rm"]
            if force:
                args.append("--force")
            args.append(container_id)
            return self.execute(*args, user=user)
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
        user=None,
    ):
        """Login to a container registry.

        :param str registry: Registry URL.
        :param str username: Username for authentication (optional if using API key).
        :param str password: Password for authentication (optional if using API key).
        :param str api_key: API key for authentication (alternative to username/password).
        :param str api_key_username: Username to use with API key authentication (default: "iamapikey" for IBM Cloud).
                                     Other registries may use different conventions (e.g., "oauth2accesstoken" for GCR).
        :param bool password_stdin: If True, read password from stdin.
        :param str user: Optional system user to run podman command as.
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
            return self.execute(*args, user=user)
        except PodmanException as ex:
            raise PodmanException(f"Failed to login to registry {registry}.") from ex

    def pull(self, image, user=None):
        """Pull an image from a registry.

        :param str image: Image name to pull.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            return self.execute("pull", image, user=user)
        except PodmanException as ex:
            raise PodmanException(f"Failed to pull image {image}.") from ex

    def stats(self, container_id, no_stream=True, user=None):
        """Get container resource usage statistics.

        :param str container_id: Container identification string.
        :param bool no_stream: If True, output stats once and exit.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["stats"]
            if no_stream:
                args.append("--no-stream")
            args.append(container_id)
            return self.execute(*args, user=user)
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

    async def execute(self, *args, user=None):
        """Execute a command and return the returncode, stdout and stderr.

        :param args: Variable length argument list to be used as argument
                      during execution.
        :param user: Optional system user to run podman command as (uses 'su - user -c').
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            LOG.debug("Executing %s", args)

            if user and user != "root":
                # Build the full podman command
                podman_cmd = [self.podman_bin] + list(args)
                podman_cmd_str = " ".join(shlex.quote(str(arg)) for arg in podman_cmd)
                su_cmd = ["su", "-", user, "-c", podman_cmd_str]
                LOG.debug("Executing as user %s: %s", user, su_cmd)
                proc = await create_subprocess_exec(
                    *su_cmd,
                    stdout=asyncio_subprocess.PIPE,
                    stderr=asyncio_subprocess.PIPE,
                )
            else:
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

    async def run(self, podman_options=None, user=None):
        """
        Run a container with command-line arguments as a list (async version).

        This is a simplified async container runner that accepts a list
        of command-line arguments to pass to 'podman run'.

        :param list podman_options: List of command-line arguments for 'podman run'.
            Example: ["-d", "--name", "test", "-e", "VAR=value",
            "--memory", "100G", "image:tag", "--model", "/path"]
        :param str user: Optional user to run podman command as (uses 'su - user -c')
        :return: tuple (returncode, stdout, stderr)
        """
        if not podman_options:
            raise PodmanException("podman_options is required")

        if not isinstance(podman_options, list):
            raise PodmanException("podman_options must be a list of strings")

        cmd_args = ["run"] + podman_options

        try:
            return await self.execute(*cmd_args, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to run container.") from ex

    async def copy_to_container(self, container_id, src, dst, user=None):
        """Copy artifacts from src to container:dst.

        This method allows copying the contents of src to the dst. Files will
        be copied from the local machine to the container. The "src" argument
        can be a file or a directory.

        :param str container_id: string with the container identification.
        :param str src: what file or directory you are trying to copy.
        :param str dst: the destination inside the container.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("cp", src, f"{container_id}:{dst}", user=user)
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

    async def get_container_info(self, container_id, user=None):
        """Return all information about specific container.

        :param container_id: identifier of container
        :type container_id: str
        :param str user: Optional system user to run podman command as.
        :rtype: dict
        """
        try:
            _, stdout, _ = await self.execute(
                "ps",
                "--all",
                "--format=json",
                "--filter",
                f"id={container_id}",
                user=user,
            )
        except PodmanException as ex:
            raise PodmanException(
                f"Failed getting information about container:" f" {container_id}."
            ) from ex
        containers = json.loads(stdout.decode())
        # Return first container if found (filter by id should return only one)
        if containers and len(containers) > 0:
            return containers[0]
        return {}

    async def start(self, container_id, user=None):
        """Starts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to start.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("start", container_id, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to start the container.") from ex

    async def stop(self, container_id, user=None):
        """Stops a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to stop.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute("stop", "-t=0", container_id, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to stop the container.") from ex

    async def restart(self, container_id, timeout=10, user=None):
        """Restarts a container and return the returncode, stdout and stderr.

        :param str container_id: Container identification string to restart.
        :param int timeout: Timeout in seconds to wait for container to stop before killing it (default: 10).
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout and stderr.
        """
        try:
            return await self.execute(
                "restart", f"-t={timeout}", container_id, user=user
            )
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
        podman_user=None,
    ):
        """Execute a command in a running container.

        :param str container_id: Container identification string.
        :param str or list command: Command to execute. Can be a string or list of arguments.
        :param str user: Optional user to run the command as inside container (e.g., "root", "1000", "1000:1000").
        :param str workdir: Optional working directory for the command.
        :param dict env: Optional dictionary of environment variables to set.
        :param bool interactive: Keep STDIN open even if not attached (default: False).
        :param bool tty: Allocate a pseudo-TTY (default: False).
        :param str podman_user: Optional system user to run podman command as.
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

            return await self.execute(*cmd_args, user=podman_user)
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
        user=None,
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
        :param str user: Optional system user to run podman command as.
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

            # Build the command string using shlex.join to properly quote arguments
            podman_cmd_str = shlex.join(podman_cmd)
            # Build the full command with optional timeout
            if timeout:
                # Use timeout command to automatically stop after specified duration
                base_command = f"timeout {timeout} {podman_cmd_str} | tee {output_file}"
            else:
                # Run indefinitely without timeout
                base_command = f"{podman_cmd_str} | tee {output_file}"
            # Wrap with su if user is specified
            if user and user != "root":
                full_command = f"su - {user} -c {shlex.quote(f'nohup bash -c {shlex.quote(base_command)} > /dev/null 2>&1 &')}"
            else:
                full_command = (
                    f"nohup bash -c {shlex.quote(base_command)} > /dev/null 2>&1 &"
                )
            LOG.info("Starting background stats collection: %s", full_command)
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

    async def list_containers(self, all_containers=True, user=None):
        """List containers.

        :param bool all_containers: If True, list all containers including stopped ones.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout (JSON list), stderr.
        """
        try:
            args = ["ps", "--format=json"]
            if all_containers:
                args.append("--all")
            return await self.execute(*args, user=user)
        except PodmanException as ex:
            raise PodmanException("Failed to list containers.") from ex

    async def logs(self, container_id, follow=False, tail=None, user=None):
        """Get container logs.

        :param str container_id: Container identification string.
        :param bool follow: If True, follow log output.
        :param int tail: Number of lines to show from the end of the logs.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["logs"]
            if follow:
                args.append("--follow")
            if tail is not None:
                args.extend(["--tail", str(tail)])
            args.append(container_id)
            return await self.execute(*args, user=user)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to get logs for container {container_id}."
            ) from ex

    async def inspect(self, container_id, user=None):
        """Inspect a container and return detailed information.

        :param str container_id: Container identification string.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout (JSON), stderr.
        """
        try:
            return await self.execute("inspect", container_id, user=user)
        except PodmanException as ex:
            raise PodmanException(
                f"Failed to inspect container {container_id}."
            ) from ex

    async def remove(self, container_id, force=False, user=None):
        """Remove a container.

        :param str container_id: Container identification string.
        :param bool force: If True, force removal of running container.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["rm"]
            if force:
                args.append("--force")
            args.append(container_id)
            return await self.execute(*args, user=user)
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
        user=None,
    ):
        """Login to a container registry.

        :param str registry: Registry URL.
        :param str username: Username for authentication (optional if using API key).
        :param str password: Password for authentication (optional if using API key).
        :param str api_key: API key for authentication (alternative to username/password).
        :param str api_key_username: Username to use with API key authentication (default: "iamapikey" for IBM Cloud).
                                     Other registries may use different conventions (e.g., "oauth2accesstoken" for GCR).
        :param bool password_stdin: If True, read password from stdin.
        :param str user: Optional system user to run podman command as.
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
            return await self.execute(*args, user=user)
        except PodmanException as ex:
            raise PodmanException(f"Failed to login to registry {registry}.") from ex

    async def pull(self, image, user=None):
        """Pull an image from a registry.

        :param str image: Image name to pull.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            return await self.execute("pull", image, user=user)
        except PodmanException as ex:
            raise PodmanException(f"Failed to pull image {image}.") from ex

    async def stats(self, container_id, no_stream=True, user=None):
        """Get container resource usage statistics.

        :param str container_id: Container identification string.
        :param bool no_stream: If True, output stats once and exit.
        :param str user: Optional system user to run podman command as.
        :rtype: tuple with returncode, stdout, stderr.
        """
        try:
            args = ["stats"]
            if no_stream:
                args.append("--no-stream")
            args.append(container_id)
            return await self.execute(*args, user=user)
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

    async def save_container_logs(
        self, container_id, log_dir, test_name="test", user=None
    ):
        """
        Save complete container logs to a file.

        :param container_id: Container ID
        :param log_dir: Directory to save logs
        :param test_name: Test name for log file naming (default: "test")
        :param user: Username if container was created by specific user
        :return: Path to saved log file or None
        """
        return save_container_logs(container_id, log_dir, test_name, user, LOG)

    async def wait_for_vllm_startup(
        self,
        container_id,
        success_pattern="Application startup complete.",
        failure_pattern=None,
        additional_failure_checks=None,
        timeout=300,
        check_interval=10,
        user=None,
        show_live_logs=True,
        live_log_lines=10,
    ):
        """
        Async method: Wait for container to start by checking logs for a success pattern.

        This is a generic async method that can be used for any container type.
        The success and failure patterns can be customized based on the application.

        :param container_id: Container ID to monitor
        :param success_pattern: String pattern to look for in logs indicating successful startup
        :param failure_pattern: Optional string pattern indicating startup failure (e.g., "BACKTRACE")
        :param additional_failure_checks: Optional list of tuples [(pattern, case_sensitive), ...]
                                         for additional failure detection. Example:
                                         [("VFIO", False), ("fail", False)] checks for "VFIO" and "fail"
        :param timeout: Maximum time to wait in seconds (default: 300)
        :param check_interval: Time between log checks in seconds (default: 10)
        :param user: Username if container was created by specific user
        :param show_live_logs: If True, display recent log lines during each check (default: True)
        :param live_log_lines: Number of recent log lines to display (default: 10)
        :return: True if startup successful, False otherwise
        """
        return wait_for_vllm_startup(
            container_id,
            success_pattern,
            failure_pattern,
            additional_failure_checks,
            timeout,
            check_interval,
            user,
            show_live_logs,
            live_log_lines,
        )
