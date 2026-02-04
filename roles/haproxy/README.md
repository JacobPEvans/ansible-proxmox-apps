# haproxy

> **DEPRECATED**: This role is deprecated in favor of `cribl_docker_stack`.
> Docker Swarm's ingress network provides native load balancing, eliminating
> the need for a separate HAProxy/Nginx layer. Use the `cribl_docker_stack`
> role for new deployments. This role will be removed in a future release.

Deploy HAProxy (TCP/HTTP) and Nginx Stream (UDP) for protocol-specific load balancing.

## Purpose

Installs and configures two complementary load balancers:

- **HAProxy**: Load balances TCP and HTTP traffic to Cribl Edge nodes
- **Nginx Stream Module**: Load balances UDP traffic (syslog, NetFlow) to
  Cribl Edge nodes

This architecture follows proper separation of concerns - each service
handles the protocols it's designed for.

## Architecture

```text
UDP (syslog/NetFlow) → Nginx stream → UDP load balance → Cribl Edge
TCP/HTTP             → HAProxy      → TCP load balance → Cribl Edge
```

Both services run on the same container (VMID 175) but handle different protocols.

## Requirements

- Debian-based OS
- Network connectivity to backend Cribl Edge nodes
- Ports 1514-1518, 2055 (syslog/NetFlow) and 8404 (HAProxy stats) available

## Role Variables

All variables in `defaults/main.yml` are user-configurable.

### Key Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `haproxy_service_state` | started | HAProxy service state |
| `haproxy_service_enabled` | true | Enable HAProxy on boot |
| `nginx_service_state` | started | Nginx service state |
| `nginx_service_enabled` | true | Enable Nginx on boot |
| `haproxy_listen_ports` | 1514-1518, 2055 | TCP frontend ports |
| `nginx_udp_ports` | 1514-1518, 2055 | UDP frontend ports |
| `haproxy_backends` | cribl-edge-* | Backend Cribl Edge nodes |
| `haproxy_stats_port` | 8404 | HAProxy admin interface |

## Examples

### Basic Deployment

```yaml
- name: Deploy load balancers
  hosts: haproxy_group
  roles:
    - haproxy
```

## Accessing Statistics

HAProxy statistics dashboard:

- URL: `http://192.168.0.175:8404/stats` (replace with your HAProxy IP)
- Username: admin
- Password: (set via `HAPROXY_STATS_PASSWORD` environment variable)

## Load Balancing Behavior

### HAProxy (TCP/HTTP)

- Algorithm: round-robin
- Health checks: TCP port 1514, interval 5s, timeout 5s
- Persistence: None (stateless syslog)
- Protocol: TCP only

### Nginx Stream (UDP)

- Algorithm: round-robin (default)
- Health checks: None (UDP is stateless)
- Persistence: None
- Protocol: UDP only

## Tasks

- Install HAProxy and Nginx
- Generate HAProxy configuration (TCP/HTTP only)
- Generate Nginx stream configuration (UDP only)
- Configure frontend listening ports for both services
- Configure backend servers
- Ensure both services are running and enabled

## Handlers

- `reload haproxy`: Reload HAProxy configuration
- `reload nginx`: Reload Nginx configuration
