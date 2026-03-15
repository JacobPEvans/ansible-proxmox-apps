"""Tier 3: Index routing and protocol-specific forwarding tests.

Validates that syslog, NetFlow, and HEC data are routed to the correct
Splunk indexes with proper sourcetype assignment.
"""

import json
import os
import ssl
import time
import urllib.error
import urllib.request
import uuid

import pytest

from .helpers import (
    query_splunk,
    send_netflow_v5,
    send_udp_syslog,
    wait_for_event,
)


class TestIndexRouting:
    """Verify syslog ports route to the correct Splunk indexes."""

    def test_unifi_index_routing(
        self, haproxy_host, constants, splunk_creds
    ):
        """Verify port 1514 (UniFi) routes to index=unifi.

        Sends a syslog message to the UniFi port and confirms it appears
        in the unifi index within the timeout period.
        """
        mgmt_url, user, password = splunk_creds
        port = constants["syslog_ports"]["unifi"]
        sentinel = (
            f"e2e-unifi-idx-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        )
        message = (
            f"<14>1 {time.strftime('%Y-%m-%dT%H:%M:%SZ')} testhost "
            f"e2e-test - - - {sentinel}"
        )

        send_udp_syslog(haproxy_host, port, message)

        results = wait_for_event(
            mgmt_url, user, password, sentinel, index="unifi", timeout=120
        )
        assert len(results) > 0, (
            f"UniFi index routing: sentinel '{sentinel}' not found in "
            f"index=unifi after 120s"
        )

    def test_firewall_index_routing(
        self, haproxy_host, constants, splunk_creds
    ):
        """Verify port 1515 (Palo Alto) routes to index=firewall.

        Sends a syslog message to the Palo Alto port and confirms it
        appears in the firewall index within the timeout period.
        """
        mgmt_url, user, password = splunk_creds
        port = constants["syslog_ports"]["palo_alto"]
        sentinel = (
            f"e2e-fw-idx-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        )
        message = (
            f"<14>1 {time.strftime('%Y-%m-%dT%H:%M:%SZ')} testhost "
            f"e2e-test - - - {sentinel}"
        )

        send_udp_syslog(haproxy_host, port, message)

        results = wait_for_event(
            mgmt_url, user, password, sentinel, index="firewall", timeout=120
        )
        assert len(results) > 0, (
            f"Firewall index routing: sentinel '{sentinel}' not found in "
            f"index=firewall after 120s"
        )


class TestNetFlow:
    """Verify NetFlow v5 data is routed to the correct index."""

    def test_netflow_routing(
        self, haproxy_host, constants, splunk_creds
    ):
        """Verify NetFlow v5 UDP traffic routes to index=network.

        Sends a minimal NetFlow v5 packet to the NetFlow port on the
        HAProxy host and verifies data appears in the network index.
        """
        mgmt_url, user, password = splunk_creds
        port = constants["netflow_ports"]["unifi"]

        # Use a unique src_port as a sentinel to correlate the test packet
        sentinel_port = 40000 + (int(time.time()) % 25000)
        send_netflow_v5(haproxy_host, port, src_port=sentinel_port)

        # Filter by the sentinel src_port to avoid matching pre-existing traffic
        search_str = (
            f'search index=network earliest=-5m src_port={sentinel_port} '
            f'| head 5'
        )
        deadline = time.time() + 120

        results = []
        while time.time() < deadline:
            result = query_splunk(
                mgmt_url, user, password, search_str, timeout=30
            )
            results = result.get("results", [])
            if results:
                break
            time.sleep(10)

        assert len(results) > 0, (
            f"NetFlow routing: no events with src_port={sentinel_port} "
            f"found in index=network after 120s"
        )


class TestHECDirect:
    """Verify direct HEC POST to Splunk works."""

    def test_hec_direct_post(self, splunk_host, constants):
        """POST an event directly to Splunk HEC and verify HTTP 200.

        Uses the SPLUNK_HEC_TOKEN environment variable to authenticate.
        This tests the HEC endpoint independently of the syslog pipeline.
        """
        hec_token = os.environ.get("SPLUNK_HEC_TOKEN")
        if not hec_token:
            pytest.skip("SPLUNK_HEC_TOKEN environment variable not set")

        port = constants["service_ports"]["splunk_hec"]
        url = f"https://{splunk_host}:{port}/services/collector/event"
        sentinel = f"e2e-hec-{uuid.uuid4().hex[:8]}-{int(time.time())}"

        payload = json.dumps({
            "event": f"E2E HEC test: {sentinel}",
            "sourcetype": "e2e:hec:test",
            "index": "main",
        }).encode("utf-8")

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Splunk {hec_token}",
                "Content-Type": "application/json",
            },
        )
        handler = urllib.request.HTTPSHandler(context=ssl_ctx)
        opener = urllib.request.build_opener(handler)

        try:
            response = opener.open(req, timeout=10)
            assert response.status == 200, (
                f"HEC POST returned {response.status}, expected 200"
            )
        except urllib.error.URLError as exc:
            pytest.fail(f"HEC POST failed at {url}: {exc}")
