# Ansible Proxmox Apps - AI Agent Documentation

Repository for Ansible automation of applications running on Proxmox VMs
and containers.

## Repository Purpose

Deploy and configure application stacks on Proxmox VMs:

- Cribl Edge: Distributed syslog log processor with persistent queuing
- Cribl Stream: Central processing node for log pipeline
- HAProxy: Syslog load balancer

Applications are deployed to VMs provisioned by `terraform-proxmox`. This
repository handles application-level configuration only (NOT Proxmox
infrastructure).

## Dependencies

### Upstream Repositories

- **terraform-proxmox**: VM provisioning and persistent storage setup
  - Creates VMs with Debian OS
  - Provisions 100GB persistent disks at `/opt/cribl/data`
  - Manages networking and storage backend

### External Services

- **Doppler**: Secrets management for API tokens and passwords

## Inventory Structure

Inventory is built entirely from environment variables (Doppler secrets).
No hardcoded values are stored in git.

### Required Environment Variables

IP addresses are **NEVER** hardcoded. They are derived at runtime:

```text
${GATEWAY_PREFIX} = first 3 octets of PROXMOX_VE_GATEWAY
Host IP = ${GATEWAY_PREFIX}.{VMID}
```

| Component | VMID | IP Pattern |
| --- | --- | --- |
| HAProxy | 175 | `${GATEWAY_PREFIX}.175` |
| Splunk | 200 | `${GATEWAY_PREFIX}.200` |
| Docker Swarm | 250 | `${GATEWAY_PREFIX}.250` |

| Variable | Purpose |
| --- | --- |
| `PROXMOX_VE_HOSTNAME` | Proxmox VE hostname |
| `PROXMOX_SSH_KEY_PATH` | Path to SSH key for Proxmox |
| `PROXMOX_VE_GATEWAY` | Network gateway IP (used to derive host IPs) |
| `PROXMOX_DOMAIN` | Internal DNS domain |
| `SPLUNK_HEC_TOKEN` | Splunk HTTP Event Collector token (secret) |

### Container Connection

LXC containers use `community.general.proxmox_pct_remote` connection plugin:

- Connects via SSH to Proxmox host
- Uses `pct exec` to run commands in containers
- No SSH required on containers themselves
- Requires community.general >= 10.3.0

### Groups

- `lxc_containers`: All LXC containers (uses pct_remote connection)
- `cribl_edge`: Nodes 1 and 2 (syslog ingestion)
- `cribl_stream_group`: Central processing node
- `haproxy_group`: Load balancer frontend
- `splunk_group`: Destination Splunk instance

## Network Architecture

### Syslog Port Assignments

| Port | Protocol | Service | Listener |
| --- | --- | --- | --- |
| 1514 | UDP/TCP | Syslog | HAProxy → Cribl Edge |
| 1515 | UDP/TCP | Syslog | HAProxy → Cribl Edge |
| 1516 | UDP/TCP | Syslog | HAProxy → Cribl Edge |
| 1517 | UDP/TCP | Syslog | HAProxy → Cribl Edge |
| 1518 | UDP/TCP | Syslog | HAProxy → Cribl Edge |
| 8088 | TCP | Splunk HEC | Cribl → Splunk |
| 8404 | TCP | HAProxy | Admin interface |

HAProxy load balances ports 1514-1518 across two Cribl Edge nodes using
round-robin with health checks.

## Cribl Configuration

### Cribl Edge

**Listeners** (Inbound):

- Syslog source: Ports 1514-1518 (UDP/TCP)
- Configured via Cribl Web UI or API after installation

**Outputs** (Outbound):

- Splunk HEC: `https://splunk-vm:8088/services/collector`
- Authentication: HEC token from Doppler

**Persistent Queue**:

- Location: `/opt/cribl/data/queue`
- Size: 100GB (mounted from terraform-proxmox provisioned disk)
- Purpose: Buffer logs during Splunk outages or high load

### Cribl Stream

**Mode**: Processing node (receives from Edge, forwards to outputs)

**Role in Pipeline**:

1. Receives parsed events from Cribl Edge nodes
2. Applies data transformation rules
3. Forwards to Splunk via HEC

**Persistent Storage**:

- Location: `/opt/cribl/data/queue`
- Size: 100GB (mounted from terraform-proxmox provisioned disk)

## Agent Tasks

### Installation and Deployment

When assigned tasks in this repository:

1. **Verify terraform-proxmox state**: Ensure VMs exist and networking is
   configured
2. **Run site.yml**: Deploy all roles via main playbook
3. **Validate health**: Verify services are running and syslog is flowing
4. **Check persistent storage**: Confirm 100GB mounts are accessible

### Configuration Changes

- Modify `roles/*/defaults/main.yml` for feature toggles
- Use `roles/*/templates/` for complex configuration files
- Always test with `--check --diff` before applying
- Run linting: `uv run ansible-lint` before commit

### Troubleshooting

Common issues and resolution:

- **Syslog not flowing**: Check HAProxy backend health and Cribl listeners
- **Persistent queue full**: Monitor `/opt/cribl/data` disk usage
- **Splunk connection errors**: Verify HEC token and HTTPS certificate

## Secrets Management

All secrets (API tokens, HEC tokens, passwords) are managed via Doppler:

```bash
# Download secrets for local testing
doppler secrets download --no-file

# Run playbook with secrets
doppler run -- ~/.local/pipx/venvs/ansible/bin/ansible-playbook \
  -i inventory/hosts.yml playbooks/site.yml
```

Never commit secrets to git. Use `.gitignore` to exclude:

- `.env` files
- `group_vars/**/secrets.yml`
- `host_vars/**/secrets.yml`

## Development Workflow

1. Create worktree for feature branch
2. Modify playbooks/roles in dedicated branch
3. Test with `--check --diff`
4. Validate with `ansible-lint`
5. Commit and push
6. Create PR for review

See CLAUDE.md in `/Users/jevans/CLAUDE.md` for worktree requirements.

## Linting and Validation

```bash
# Lint all Ansible files
~/.local/pipx/venvs/ansible/bin/ansible-lint

# Check specific role
~/.local/pipx/venvs/ansible/bin/ansible-lint roles/cribl_edge/

# Check playbook syntax
doppler run -- ~/.local/pipx/venvs/ansible/bin/ansible-playbook \
  -i inventory/hosts.yml playbooks/site.yml --syntax-check

# Dry run with diff
doppler run -- ~/.local/pipx/venvs/ansible/bin/ansible-playbook \
  -i inventory/hosts.yml playbooks/site.yml --check --diff
```

## Related Repositories

- **terraform-proxmox**: Infrastructure provisioning (VMs, storage, network)
- **ansible-proxmox**: Proxmox cluster configuration (NOT this repo)

## Skill Documentation

This repository uses these Ansible skills:

- `ansible-fundamentals`: Core module patterns, FQCN, collections
- `ansible-idempotency`: changed_when, failed_when, idempotency checks
- `ansible-proxmox`: Proxmox-specific patterns
- `ansible-secrets`: Doppler integration, no_log patterns
- `ansible-playbook-design`: Playbook structure, variable organization
- `ansible-role-design`: Role structure, defaults, handlers

All code must follow patterns defined in these skills.
