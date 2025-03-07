import socket
import time


def is_network_available(host="google.com", port=80, timeout=5):
    """
    Check if network is available by trying to connect to a well-known host.

    :param host: Host to connect to
    :param port: Port to connect to
    :param timeout: Timeout in seconds
    :return: True if network is available, False otherwise
    """
    try:
        # Try to create a socket connection to the host
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except (socket.timeout, socket.error):
        return False


def wait_for_network(
    host="google.com", port=80, timeout=5, max_retries=3, retry_delay=1
):
    """
    Wait for network to be available.

    :param host: Host to connect to
    :param port: Port to connect to
    :param timeout: Timeout in seconds for each connection attempt
    :param max_retries: Maximum number of retries
    :param retry_delay: Delay between retries in seconds
    :return: True if network is available, False otherwise
    """
    for _ in range(max_retries):
        if is_network_available(host, port, timeout):
            return True
        time.sleep(retry_delay)
    return False
