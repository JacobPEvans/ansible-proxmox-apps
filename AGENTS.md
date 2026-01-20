# Ansible Proxmox Apps - AI Agent Documentation

Ansible automation for applications running on Proxmox VMs and containers.

## Purpose

Deploy and configure application stacks on Proxmox VMs:

- Cribl Edge: Distributed syslog log processor with persistent queuing
- Cribl Stream: Central processing node for log pipeline
- HAProxy: Syslog load balancer

**NOTE**: Splunk configuration has been moved to `ansible-splunk` repository.
The `splunk_docker` role in this repo is deprecated.

## Dependencies

### Upstream Repositories

- **terraform-proxmox**: VM provisioning and persistent storage setup
  - Creates VMs with Debian OS
  - Provisions 100GB persistent disks at `/opt/cribl/data`
  - Manages networking and storage backend

### External Services

- **Doppler**: Secrets management for API tokens and passwords

## Key Files

| Path | Purpose |
| ---- | ------- |
| `roles/cribl_edge/` | Cribl Edge deployment |
| `roles/cribl_stream/` | Cribl Stream deployment |
| `playbooks/site.yml` | Main orchestration playbook |
| `inventory/hosts.yml` | Static inventory |
| `inventory/load_terraform.yml` | Dynamic inventory loader |

## Deprecated

- `roles/splunk_docker/` - **DEPRECATED**: Use `ansible-splunk` instead

## Network Architecture

### Syslog Port Assignments

| Port | Protocol | Service | Listener |
| ---- | -------- | ------- | -------- |
| 1514 | UDP/TCP | Syslog | HAProxy to Cribl Edge |
| 1515 | UDP/TCP | Syslog | HAProxy to Cribl Edge |
| 1516 | UDP/TCP | Syslog | HAProxy to Cribl Edge |
| 1517 | UDP/TCP | Syslog | HAProxy to Cribl Edge |
| 1518 | UDP/TCP | Syslog | HAProxy to Cribl Edge |
| 8088 | TCP | Splunk HEC | Cribl to Splunk |

## Agent Tasks

### Deployment

```bash
doppler run -- uv run ansible-playbook playbooks/site.yml
```

### Troubleshooting

- **Syslog not flowing**: Check HAProxy backend health
- **Persistent queue full**: Monitor `/opt/cribl/data` disk usage
- **Splunk errors**: Use `ansible-splunk` repo for Splunk issues

## Secrets Management

All secrets from Doppler:

```bash
doppler run -- uv run ansible-playbook playbooks/site.yml
```

## Related Repositories

- **terraform-proxmox**: Infrastructure provisioning
- **ansible-proxmox**: Proxmox host configuration
- **ansible-splunk**: Splunk configuration (moved from here)
