"""Pure utility functions for E2E pipeline tests.

Uses Python stdlib only: socket, urllib, struct, json, time.
No third-party dependencies.
"""

import json
import socket
import ssl
import struct
import time
import urllib.parse
import urllib.request


def send_udp_syslog(host, port, message):
    """Send a syslog message via UDP.

    Args:
        host: Target hostname or IP address.
        port: Target UDP port number.
        message: Syslog message string to send.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(message.encode("utf-8"), (host, port))
    finally:
        sock.close()


def send_tcp_syslog(host, port, message):
    """Send a syslog message via TCP.

    Args:
        host: Target hostname or IP address.
        port: Target TCP port number.
        message: Syslog message string to send.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((host, port))
        sock.sendall(message.encode("utf-8") + b"\n")
    finally:
        sock.close()


def query_splunk(mgmt_url, user, password, search_str, timeout=120):
    """Execute a oneshot search against Splunk REST API.

    Args:
        mgmt_url: Splunk management URL (e.g., https://10.0.1.200:8089).
        user: Splunk username.
        password: Splunk password.
        search_str: SPL search string (must start with 'search').
        timeout: HTTP request timeout in seconds.

    Returns:
        Parsed JSON response dict from Splunk.
    """
    url = f"{mgmt_url}/services/search/jobs"
    data = (
        f"search={urllib.parse.quote(search_str)}"
        f"&output_mode=json"
        f"&exec_mode=oneshot"
    ).encode("utf-8")

    # Set up basic auth
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, url, user, password)
    auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)

    # Disable SSL cert verification for self-signed certs
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    https_handler = urllib.request.HTTPSHandler(context=ssl_ctx)

    opener = urllib.request.build_opener(auth_handler, https_handler)

    req = urllib.request.Request(url, data=data, method="POST")
    with opener.open(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_event(mgmt_url, user, password, sentinel, index, timeout=120):
    """Poll Splunk until an event containing the sentinel string appears.

    Args:
        mgmt_url: Splunk management URL.
        user: Splunk username.
        password: Splunk password.
        sentinel: Unique string to search for in events.
        index: Splunk index to search in.
        timeout: Maximum time in seconds to wait for the event.

    Returns:
        List of matching result dicts from Splunk.

    Raises:
        TimeoutError: If the event is not found within the timeout period.
    """
    search_str = f'search index={index} "{sentinel}" | head 5'
    deadline = time.time() + timeout

    while time.time() < deadline:
        result = query_splunk(mgmt_url, user, password, search_str, timeout=30)
        results = result.get("results", [])
        if results:
            return results
        time.sleep(10)

    raise TimeoutError(
        f"Event with sentinel '{sentinel}' not found in index={index} "
        f"within {timeout}s"
    )


def send_netflow_v5(host, port):
    """Send a minimal NetFlow v5 packet via UDP.

    Constructs a valid NetFlow v5 header with one flow record and sends
    it to the specified host and port. The flow record contains minimal
    data sufficient for Cribl Edge to recognize and route it.

    Args:
        host: Target hostname or IP address.
        port: Target UDP port number.
    """
    unix_secs = int(time.time())

    # NetFlow v5 header: 24 bytes
    # version(2), count(2), sys_uptime(4), unix_secs(4), unix_nsecs(4),
    # flow_sequence(4), engine_type(1), engine_id(1), sampling_interval(2)
    header = struct.pack(
        "!HHIIIIBBH",
        5,           # version
        1,           # count (1 flow record)
        0,           # sys_uptime
        unix_secs,   # unix_secs
        0,           # unix_nsecs
        1,           # flow_sequence
        0,           # engine_type
        0,           # engine_id
        0,           # sampling_interval
    )

    # NetFlow v5 flow record: 48 bytes
    # src_addr(4), dst_addr(4), nexthop(4), input(2), output(2),
    # packets(4), octets(4), first(4), last(4),
    # src_port(2), dst_port(2), pad1(1), tcp_flags(1), proto(1), tos(1),
    # src_as(2), dst_as(2), src_mask(1), dst_mask(1), pad2(2)
    flow_record = struct.pack(
        "!IIIHHIIIIHHBBBBHHBBH",
        0x0A000101,  # src_addr: 10.0.1.1
        0x0A000102,  # dst_addr: 10.0.1.2
        0,           # nexthop
        0,           # input interface
        0,           # output interface
        1,           # packets
        64,          # octets
        0,           # first
        0,           # last
        12345,       # src_port
        80,          # dst_port
        0,           # pad1
        0,           # tcp_flags
        6,           # proto (TCP)
        0,           # tos
        0,           # src_as
        0,           # dst_as
        24,          # src_mask
        24,          # dst_mask
        0,           # pad2
    )

    packet = header + flow_record

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(packet, (host, port))
    finally:
        sock.close()


def check_port_tcp(host, port, timeout=2):
    """Check if a TCP port is accepting connections.

    Args:
        host: Target hostname or IP address.
        port: Target TCP port number.
        timeout: Connection timeout in seconds.

    Returns:
        True if the port is open and accepting connections, False otherwise.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def check_port_udp(host, port, timeout=2):
    """Check if a UDP port is reachable (best effort).

    Sends an empty datagram and checks for ICMP unreachable response.
    Note: UDP port checks are inherently unreliable since the protocol
    is connectionless. A True result means no rejection was received,
    not necessarily that a service is listening.

    Args:
        host: Target hostname or IP address.
        port: Target UDP port number.
        timeout: Timeout in seconds to wait for ICMP unreachable.

    Returns:
        True if no rejection was received, False if port is definitely closed.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(b"", (host, port))
        try:
            sock.recvfrom(1024)
        except socket.timeout:
            # No ICMP unreachable received -- port is likely open
            return True
        return True
    except (ConnectionRefusedError, OSError):
        return False
    finally:
        sock.close()
