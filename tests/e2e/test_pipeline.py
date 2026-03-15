"""Tier 2: Full-path data flow pipeline tests.

Sends syslog data through the pipeline and verifies it arrives in
the correct Splunk index. Tests both the HAProxy-fronted path and
the direct-to-LXC path.
"""

import time
import uuid

import pytest

from .helpers import send_udp_syslog, wait_for_event


# Map syslog port names to their expected Splunk index
SYSLOG_PORT_INDEX_MAP = {
    "unifi": "unifi",
    "palo_alto": "firewall",
    "cisco_asa": "firewall",
    "linux": "os",
    "windows": "os",
}


class TestSyslogViaHAProxy:
    """Tests that send syslog through HAProxy to Splunk."""

    def test_syslog_via_haproxy(self, haproxy_host, constants, splunk_creds):
        """Send a UDP syslog message via HAProxy and verify it reaches Splunk.

        Sends a uniquely identifiable syslog message to HAProxy on the
        UniFi syslog port (1514) and waits up to 120 seconds for it to
        appear in the unifi index in Splunk.
        """
        mgmt_url, user, password = splunk_creds
        port = constants["syslog_ports"]["unifi"]
        sentinel = f"e2e-haproxy-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        message = (
            f"<14>1 {time.strftime('%Y-%m-%dT%H:%M:%SZ')} testhost "
            f"e2e-test - - - {sentinel}"
        )

        send_udp_syslog(haproxy_host, port, message)

        results = wait_for_event(
            mgmt_url, user, password, sentinel, index="unifi", timeout=120
        )
        assert len(results) > 0, (
            f"Syslog via HAProxy: sentinel '{sentinel}' not found in "
            f"index=unifi after 120s"
        )


class TestSyslogDirectToLXC:
    """Tests that send syslog directly to Cribl Edge LXC containers."""

    def test_syslog_direct_to_lxc(
        self, cribl_edge_ips, constants, splunk_creds
    ):
        """Send a UDP syslog message directly to a Cribl Edge LXC and verify.

        Bypasses HAProxy and sends directly to the first Cribl Edge LXC
        on the UniFi syslog port, then verifies the event arrives in Splunk.
        """
        mgmt_url, user, password = splunk_creds
        port = constants["syslog_ports"]["unifi"]
        edge_ip = cribl_edge_ips[0]
        sentinel = f"e2e-direct-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        message = (
            f"<14>1 {time.strftime('%Y-%m-%dT%H:%M:%SZ')} testhost "
            f"e2e-test - - - {sentinel}"
        )

        send_udp_syslog(edge_ip, port, message)

        results = wait_for_event(
            mgmt_url, user, password, sentinel, index="unifi", timeout=120
        )
        assert len(results) > 0, (
            f"Syslog direct to LXC: sentinel '{sentinel}' not found in "
            f"index=unifi after 120s"
        )

    @pytest.mark.parametrize(
        "port_name,expected_index",
        list(SYSLOG_PORT_INDEX_MAP.items()),
        ids=list(SYSLOG_PORT_INDEX_MAP.keys()),
    )
    def test_syslog_port_routing(
        self,
        cribl_edge_ips,
        constants,
        splunk_creds,
        port_name,
        expected_index,
    ):
        """Verify each syslog port routes to the correct Splunk index.

        Sends a uniquely identifiable syslog message to each port on
        the first Cribl Edge LXC and confirms it lands in the expected
        Splunk index based on the port-to-index routing configuration.
        """
        mgmt_url, user, password = splunk_creds
        port = constants["syslog_ports"][port_name]
        edge_ip = cribl_edge_ips[0]
        sentinel = (
            f"e2e-route-{port_name}-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        )
        message = (
            f"<14>1 {time.strftime('%Y-%m-%dT%H:%M:%SZ')} testhost "
            f"e2e-test - - - {sentinel}"
        )

        send_udp_syslog(edge_ip, port, message)

        results = wait_for_event(
            mgmt_url,
            user,
            password,
            sentinel,
            index=expected_index,
            timeout=120,
        )
        assert len(results) > 0, (
            f"Port routing: sentinel '{sentinel}' sent to port {port} "
            f"({port_name}) not found in index={expected_index} after 120s"
        )
