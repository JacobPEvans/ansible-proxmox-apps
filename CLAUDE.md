# Ansible Proxmox Apps

Configure applications on Proxmox VMs and LXC containers.
VMs/containers are provisioned by `terraform-proxmox`;
this repo handles app config only.

## This Repo Owns

- **Cribl Edge/Stream** (Docker Swarm on docker-host VM)
- **HAProxy** (LXC container, legacy syslog load balancer)
- **Technitium DNS** (LXC container)
- **apt-cacher-ng** (LXC container)

**This repo does NOT own Splunk.** Splunk is managed by `ansible-splunk`.

## Pipeline Data Flow

```text
Source -> Docker Swarm Host (syslog:1514-1518/udp)
           |
       Cribl Edge (2 replicas, Swarm ingress LB)
         - Pipeline: sets index + sourcetype by port
         - Output: Splunk HEC (http, port 8088)
           |
       Splunk Enterprise (managed by ansible-splunk)
```

### Syslog Port Assignments (from terraform pipeline_constants)

| Port | Source | Splunk Index |
| --- | --- | --- |
| 1514 | UniFi | unifi |
| 1515 | Palo Alto | firewall |
| 1516 | Cisco ASA | firewall |
| 1517 | Linux | os |
| 1518 | Windows | os |

### Service Ports (from terraform pipeline_constants)

| Port | Service |
| --- | --- |
| 8000 | Splunk Web UI |
| 8088 | Splunk HEC |
| 8089 | Splunk Management |
| 8404 | HAProxy Stats |
| 9000 | Cribl Edge API |
| 9100 | Cribl Stream API |

## Inventory

Inventory is loaded dynamically from
`terraform_inventory.json` via `load_terraform.yml`.
Port constants come from `terraform_data.constants`
(defined in terraform-proxmox `locals.tf`).

### Groups (from terraform inventory)

- `lxc_containers`: All LXC containers (`proxmox_pct_remote` connection)
- `docker_vms` / `cribl_docker_group`: Docker Swarm hosts (SSH)

### Required Environment Variables

| Variable | Purpose |
| --- | --- |
| `PROXMOX_VE_HOSTNAME` | Proxmox VE hostname |
| `PROXMOX_SSH_KEY_PATH` | Path to SSH key |
| `PROXMOX_VE_GATEWAY` | Network gateway (for IP derivation) |
| `PROXMOX_DOMAIN` | Internal DNS domain |
| `SPLUNK_HEC_TOKEN` | Splunk HEC token (for Cribl output) |
| `SPLUNK_PASSWORD` | Splunk admin password (for E2E validation) |

## Commands

```bash
# Deploy all apps
doppler run -- uv run ansible-playbook -i inventory/hosts.yml playbooks/site.yml

# Validate pipeline
doppler run -- uv run ansible-playbook -i inventory/hosts.yml playbooks/validate-pipeline.yml

# E2E test only
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml \
  --tags e2e

# Lint
uv run ansible-lint
```

## Related Repositories

| Repo | Relationship |
| --- | --- |
| terraform-proxmox | Upstream: provisions VMs/containers |
| ansible-splunk | Peer: owns Splunk Enterprise deployment |
| ansible-proxmox | Peer: owns Proxmox host config (kernel, ZFS, firewall) |
