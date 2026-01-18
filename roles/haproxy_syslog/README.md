# haproxy_syslog

Deploy HAProxy configured for syslog load balancing.

## Purpose

Installs and configures HAProxy to load balance syslog traffic across Cribl
Edge nodes. Handles both UDP and TCP on ports 1514-1518 with health checks
and statistics dashboard.

## Requirements

- Debian-based OS
- Network connectivity to backend Cribl Edge nodes
- Ports 1514-1518 and 8404 available for listening

## Role Variables

All variables in `defaults/main.yml` are user-configurable.

### Key Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `haproxy_syslog_service_state` | started | Service state |
| `haproxy_syslog_service_enabled` | true | Enable on boot |
| `haproxy_syslog_listen_ports` | 1514-1518 | Frontend ports |
| `haproxy_syslog_backends` | cribl-edge-* | Backend servers |
| `haproxy_syslog_stats_port` | 8404 | Admin interface |

## Examples

### Basic Deployment

```yaml
- name: Deploy HAProxy
  hosts: haproxy_group
  roles:
    - haproxy_syslog
```

## Accessing Statistics

After deployment, access HAProxy statistics dashboard:

- URL: `http://haproxy-ip:8404/stats`
- Username: admin
- Password: (set via `haproxy_syslog_stats_password`)

## Load Balancing Behavior

- Algorithm: round-robin
- Health checks: TCP port 1514, interval 5s, timeout 5s
- Persistence: None (stateless syslog)
- Protocol: TCP and UDP (both)

## Tasks

- Install HAProxy
- Generate configuration from template
- Configure frontend listening ports
- Configure backend servers with health checks
- Ensure service is running and enabled

## Handlers

- `reload haproxy`: Reload HAProxy configuration
