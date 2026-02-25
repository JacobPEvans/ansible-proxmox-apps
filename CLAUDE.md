# Ansible Proxmox Apps

Configure applications on Proxmox VMs and LXC containers.
VMs/containers are provisioned by `terraform-proxmox`;
this repo handles app config only.

## This Repo Owns

- **Cribl Edge/Stream** (Docker Swarm on docker-host VM)
- **HAProxy** (LXC container, legacy syslog load balancer)
- **Technitium DNS** (LXC container)
- **apt-cacher-ng** (LXC container)
- **Mailpit** (LXC container, SMTP relay with web UI)
- **ntfy** (LXC container, push notification server)

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
| 1025 | Mailpit SMTP |
| 8025 | Mailpit Web UI |
| 8080 | ntfy HTTP |

## Inventory

Inventory is loaded dynamically from
`terraform_inventory.json` via `load_terraform.yml`.
Port constants come from `terraform_data.constants`
(defined in terraform-proxmox `locals.tf`).

### Groups (from terraform inventory)

- `lxc_containers`: All LXC containers (`proxmox_pct_remote` connection)
- `docker_vms` / `cribl_docker_group`: Docker Swarm hosts (SSH)
- `mailpit_group`: Containers tagged `smtp` (Mailpit SMTP relay)
- `ntfy_group`: Containers tagged `push` (ntfy push notifications)

### Environment Variables

| Variable | Purpose | Source |
| --- | --- | --- |
| `PROXMOX_VE_HOSTNAME` | Proxmox VE hostname | Doppler / SOPS |
| `PROXMOX_VE_NODE` | Proxmox node name | SOPS |
| `PROXMOX_VE_GATEWAY` | Network gateway (for IP derivation) | Doppler / SOPS |
| `PROXMOX_DOMAIN` | Internal DNS domain | Doppler / SOPS |
| `PROXMOX_SSH_KEY_PATH` | Path to SSH key | Doppler / SOPS |
| `SPLUNK_HEC_TOKEN` | Splunk HEC token (for Cribl output) | Doppler / SOPS |
| `SPLUNK_PASSWORD` | Splunk admin password (for E2E validation) | Doppler / SOPS |
| `HAPROXY_STATS_PASSWORD` | HAProxy stats page password | SOPS |
| `TECHNITIUM_DNS_API_TOKEN` | Technitium DNS API token | SOPS |
| `MAILPIT_RELAY_HOST` | SMTP relay hostname | SOPS |
| `MAILPIT_RELAY_PORT` | SMTP relay port (default 587) | SOPS |
| `MAILPIT_RELAY_USERNAME` | SMTP relay username | SOPS |
| `MAILPIT_RELAY_PASSWORD` | SMTP relay password / app password | Doppler / SOPS |
| `MSSQL_SA_PASSWORD` | SQL Server SA password (for mssql_docker role) | SOPS |

## Secrets Management

**Runtime injection**: Doppler (`doppler run --`)
**At-rest encryption**: SOPS + age (`secrets.enc.yaml`)

See the [SOPS integration rule](agentsmd/rules/infra/sops-integration.md)
in ai-assistant-instructions for full patterns.

Template: `secrets.enc.yaml.example` — copy, fill in real values, then encrypt.

## Commands

```bash
# Deploy all apps (Doppler-only)
doppler run -- uv run ansible-playbook -i inventory/hosts.yml playbooks/site.yml

# Deploy all apps (SOPS + Doppler overlay)
sops exec-env secrets.enc.yaml 'doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/site.yml'

# Edit encrypted secrets
sops secrets.enc.yaml

# Validate pipeline
doppler run -- uv run ansible-playbook -i inventory/hosts.yml playbooks/validate-pipeline.yml

# Lint
uv run ansible-lint
```

## Testing

### Fast (CI + pre-commit — runs automatically)

| Check | Command | When |
| --- | --- | --- |
| Ansible lint | `uv run ansible-lint` | pre-commit, every PR |
| Playbook syntax | `ansible-playbook --syntax-check` | every PR (CI) |
| Inventory group validation | see below | every PR (CI) |
| Molecule syntax | `uv run molecule syntax` | every PR (CI, roles/molecule changes) |

**Inventory validation locally:**

```bash
cp tests/inventory_load/terraform_inventory.json inventory/terraform_inventory.json
ansible-playbook tests/inventory_load/verify_inventory.yml \
  -i inventory/hosts.yml -c local
```

### Extended (manual — run before merging role changes)

Full Molecule test deploys the `mssql_docker` role in a Docker container,
starts SQL Server, and verifies port 1433 is accepting connections.
Requires Docker on the local machine (~5-10 min).

```bash
# Install Molecule dependencies (once)
uv pip install molecule 'molecule-plugins[docker]>=23.0.0' 'docker>=7.0.0'
ansible-galaxy collection install -r requirements.yml

# Run full test cycle (create -> converge -> idempotence -> verify -> destroy)
uv run molecule test

# Or step through individually for debugging
uv run molecule converge   # deploy role into container
uv run molecule verify     # run assertions
uv run molecule destroy    # clean up
```

**When to run:** Any time you modify a role in `roles/` before opening a PR.

## Related Repositories

| Repo | Relationship |
| --- | --- |
| terraform-proxmox | Upstream: provisions VMs/containers |
| ansible-splunk | Peer: owns Splunk Enterprise deployment |
| ansible-proxmox | Peer: owns Proxmox host config (kernel, ZFS, firewall) |
