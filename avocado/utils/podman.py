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

"""
This module provides an basic API for interacting with podman.

This module it was designed to be executed in async mode. Remember this when
consuming this API.
"""

import asyncio
import json
import logging
import subprocess
from asyncio import create_subprocess_exec
from asyncio import subprocess as asyncio_subprocess
from shutil import which

LOG = logging.getLogger(__name__)


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
            # Since this method is also used by other methods, let's
            # log here as well.
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
        :param str port_mapping: Port mapping in format [host_ip]:[host_port]:container_port
                                 (default: "127.0.0.1::8000" - localhost with random host port to container port 8000).
                                 Examples: "127.0.0.1:8000:8000" (fixed host port 8000),
                                          "0.0.0.0::8000" (all interfaces, random host port),
                                          "::8000" (all interfaces, random host port).
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

        # Add optional environment variables
        if vllm_dt_chunk_len is not None:
            cmd_args.extend(["-e", f"VLLM_DT_CHUNK_LEN={vllm_dt_chunk_len}"])
        if vllm_spyre_use_chunked_prefill is not None:
            cmd_args.extend(
                ["-e", f"VLLM_SPYRE_USE_CHUNKED_PREFILL={vllm_spyre_use_chunked_prefill}"]
            )

        # Add container name if provided
        if container_name:
            cmd_args.extend(["--name", container_name])

        # Add image and command arguments
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
                "--enable-prefix-caching",
            ]
        )

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
            raise PodmanException(f"Failed to get logs for container {container_id}.") from ex

    def inspect(self, container_id):
        """Inspect a container and return detailed information.

        :param str container_id: Container identification string.
        :rtype: tuple with returncode, stdout (JSON), stderr.
        """
        try:
            return self.execute("inspect", container_id)
        except PodmanException as ex:
            raise PodmanException(f"Failed to inspect container {container_id}.") from ex

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

    def login(self, registry, username=None, password=None, api_key=None, api_key_username="iamapikey", password_stdin=False):
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
            
            # API key authentication
            if api_key:
                # Use provided username or default api_key_username
                # IBM Cloud Container Registry uses "iamapikey"
                # Google Container Registry uses "oauth2accesstoken"
                # AWS ECR uses "AWS"
                args.extend(["--username", username or api_key_username])
                args.extend(["--password", api_key])
            elif username and password:
                # Traditional username/password authentication
                args.extend(["--username", username])
                if not password_stdin:
                    args.extend(["--password", password])
            elif password_stdin:
                # Password from stdin
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
            raise PodmanException(f"Failed to get stats for container {container_id}.") from ex


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
            # Since this method is also used by other methods, let's
            # log here as well.
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
        :param str port_mapping: Port mapping in format [host_ip]:[host_port]:container_port
                                 (default: "127.0.0.1::8000" - localhost with random host port to container port 8000).
                                 Examples: "127.0.0.1:8000:8000" (fixed host port 8000),
                                          "0.0.0.0::8000" (all interfaces, random host port),
                                          "::8000" (all interfaces, random host port).
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

        # Add optional environment variables
        if vllm_dt_chunk_len is not None:
            cmd_args.extend(["-e", f"VLLM_DT_CHUNK_LEN={vllm_dt_chunk_len}"])
        if vllm_spyre_use_chunked_prefill is not None:
            cmd_args.extend(
                ["-e", f"VLLM_SPYRE_USE_CHUNKED_PREFILL={vllm_spyre_use_chunked_prefill}"]
            )

        # Add container name if provided
        if container_name:
            cmd_args.extend(["--name", container_name])

        # Add image and VLLM command arguments
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
        
        # Add optional VLLM features
        if enable_prefix_caching:
            cmd_args.append("--enable-prefix-caching")
        
        # Add any additional VLLM arguments
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
            raise PodmanException(f"Failed to get logs for container {container_id}.") from ex

    async def inspect(self, container_id):
        """Inspect a container and return detailed information.

        :param str container_id: Container identification string.
        :rtype: tuple with returncode, stdout (JSON), stderr.
        """
        try:
            return await self.execute("inspect", container_id)
        except PodmanException as ex:
            raise PodmanException(f"Failed to inspect container {container_id}.") from ex

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

    async def login(self, registry, username=None, password=None, api_key=None, api_key_username="iamapikey", password_stdin=False):
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
            
            # API key authentication
            if api_key:
                # Use provided username or default api_key_username
                # IBM Cloud Container Registry uses "iamapikey"
                # Google Container Registry uses "oauth2accesstoken"
                # AWS ECR uses "AWS"
                args.extend(["--username", username or api_key_username])
                args.extend(["--password", api_key])
            elif username and password:
                # Traditional username/password authentication
                args.extend(["--username", username])
                if not password_stdin:
                    args.extend(["--password", password])
            elif password_stdin:
                # Password from stdin
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
            raise PodmanException(f"Failed to get stats for container {container_id}.") from ex

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
        # Validate AIU IDs list
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

        # Create tasks for concurrent execution
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

        # Execute all tasks concurrently using asyncio.gather
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        results = []
        for container_name, result in zip(container_names, task_results):
            if isinstance(result, Exception):
                LOG.error("Failed to create container %s: %s", container_name, str(result))
                results.append((container_name, None, None, str(result)))
            else:
                returncode, stdout, stderr = result
                results.append((container_name, returncode, stdout, stderr))
                LOG.info("Container %s created successfully", container_name)

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
            else:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))
                LOG.info("Container %s started successfully", container_id)

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
            else:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))
                LOG.info("Container %s stopped successfully", container_id)

        return output

    async def remove_multiple_containers(self, container_ids, force=False):
        """Remove multiple containers concurrently.

        :param list container_ids: List of container IDs to remove.
        :param bool force: If True, force removal of running containers.
        :rtype: list of tuples (container_id, returncode, stdout, stderr).
        """
        tasks = [self.remove(container_id, force=force) for container_id in container_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for container_id, result in zip(container_ids, results):
            if isinstance(result, Exception):
                LOG.error("Failed to remove container %s: %s", container_id, str(result))
                output.append((container_id, None, None, str(result)))
            else:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))
                LOG.info("Container %s removed successfully", container_id)

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
                LOG.error("Failed to get logs for container %s: %s", container_id, str(result))
                output.append((container_id, None, None, str(result)))
            else:
                returncode, stdout, stderr = result
                output.append((container_id, returncode, stdout, stderr))

        return output
