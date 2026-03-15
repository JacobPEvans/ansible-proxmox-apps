"""Tier 1: Service health smoke tests.

Validates that all pipeline services are running and listening on their
expected ports. No data is sent through the pipeline -- these tests only
verify TCP/UDP connectivity to each service endpoint.
"""

import ssl
import urllib.error
import urllib.request

import pytest

from .helpers import check_port_tcp, check_port_udp


class TestHAProxy:
    """HAProxy load balancer port checks."""

    @pytest.mark.parametrize(
        "port_name",
        ["unifi", "palo_alto", "cisco_asa", "linux", "windows"],
    )
    def test_haproxy_syslog_ports(self, haproxy_host, constants, port_name):
        """Verify HAProxy is accepting UDP syslog on each port."""
        port = constants["syslog_ports"][port_name]
        assert check_port_udp(haproxy_host, port), (
            f"HAProxy syslog port {port} ({port_name}) is not reachable "
            f"via UDP on {haproxy_host}"
        )

    def test_haproxy_stats(self, haproxy_host, constants):
        """Verify HAProxy stats page port is listening."""
        port = constants["service_ports"]["haproxy_stats"]
        assert check_port_tcp(haproxy_host, port), (
            f"HAProxy stats port {port} is not accepting "
            f"connections on {haproxy_host}"
        )


class TestCriblEdgeLXC:
    """Cribl Edge LXC container port checks (syslog processing)."""

    @pytest.mark.parametrize(
        "port_name",
        ["unifi", "palo_alto", "cisco_asa", "linux", "windows"],
    )
    def test_cribl_edge_syslog_ports(
        self, cribl_edge_ips, constants, port_name
    ):
        """Verify each Cribl Edge LXC is accepting syslog on each UDP port."""
        port = constants["syslog_ports"][port_name]
        for edge_ip in cribl_edge_ips:
            assert check_port_udp(edge_ip, port), (
                f"Cribl Edge syslog port {port} ({port_name}) is not "
                f"reachable on {edge_ip}"
            )

    def test_cribl_edge_api(self, cribl_edge_ips, constants):
        """Verify Cribl Edge API port is accepting TCP connections."""
        port = constants["service_ports"]["cribl_edge_api"]
        for edge_ip in cribl_edge_ips:
            assert check_port_tcp(edge_ip, port), (
                f"Cribl Edge API port {port} is not accepting "
                f"connections on {edge_ip}"
            )


class TestCriblStreamLXC:
    """Cribl Stream LXC container port checks (netflow/IPFIX processing)."""

    def test_cribl_stream_netflow(self, cribl_stream_ips, constants):
        """Verify each Cribl Stream LXC is accepting NetFlow UDP traffic."""
        port = constants["netflow_ports"]["unifi"]
        for stream_ip in cribl_stream_ips:
            assert check_port_udp(stream_ip, port), (
                f"Cribl Stream NetFlow port {port} is not "
                f"reachable on {stream_ip}"
            )

    def test_cribl_stream_api(self, cribl_stream_ips, constants):
        """Verify Cribl Stream API port is accepting TCP connections."""
        port = constants["service_ports"]["cribl_stream_api"]
        for stream_ip in cribl_stream_ips:
            assert check_port_tcp(stream_ip, port), (
                f"Cribl Stream API port {port} is not accepting "
                f"connections on {stream_ip}"
            )


class TestSplunk:
    """Splunk service port checks."""

    def test_splunk_web(self, splunk_host, constants):
        """Verify Splunk Web UI port is listening."""
        port = constants["service_ports"]["splunk_web"]
        assert check_port_tcp(splunk_host, port), (
            f"Splunk Web port {port} is not accepting "
            f"connections on {splunk_host}"
        )

    def test_splunk_hec(self, splunk_host, constants):
        """Verify Splunk HEC port is listening."""
        port = constants["service_ports"]["splunk_hec"]
        assert check_port_tcp(splunk_host, port), (
            f"Splunk HEC port {port} is not accepting "
            f"connections on {splunk_host}"
        )

    def test_splunk_hec_health(self, splunk_host, constants):
        """Verify Splunk HEC health endpoint returns HTTP 200.

        The HEC health endpoint at /services/collector/health/1.0 responds
        with 200 when HEC is enabled and accepting events.
        """
        port = constants["service_ports"]["splunk_hec"]
        url = f"https://{splunk_host}:{port}/services/collector/health/1.0"

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, method="GET")
        handler = urllib.request.HTTPSHandler(context=ssl_ctx)
        opener = urllib.request.build_opener(handler)

        try:
            with opener.open(req, timeout=10) as response:
                assert response.status == 200, (
                    f"Splunk HEC health endpoint returned {response.status}, "
                    f"expected 200"
                )
        except urllib.error.URLError as exc:
            pytest.fail(
                f"Splunk HEC health endpoint unreachable at {url}: {exc}"
            )
