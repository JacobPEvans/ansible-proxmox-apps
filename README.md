# Ansible Proxmox Apps

Configure applications running on Proxmox VMs and containers.

This repository manages application deployment and configuration on virtual
machines and containers provisioned by Proxmox VE. For Proxmox infrastructure
provisioning, see `terraform-proxmox`.

## Purpose and Scope

Deploy and configure the following application stacks:

- **Cribl Edge**: Syslog ingestion and log processing with persistent queue
- **Cribl Stream**: Central processing node for log pipeline
- **HAProxy**: Syslog load balancer distributing logs to Cribl Edge nodes

All applications run on Proxmox VMs. VMs and storage are provisioned by
`terraform-proxmox`. This repository handles application configuration only.

## Dependencies

- **terraform-proxmox**: Provisions VMs and persistent storage
- **Doppler**: Secrets management (API keys, passwords)
- Ansible 2.12+
- Python 3.9+

## Quick Start

### 1. Clone Repository

```bash
cd ~/git
git clone <repo-url> ansible-proxmox-apps
cd ansible-proxmox-apps
```

### 2. Install Dependencies

```bash
pip install ansible==2.12.0
uv run ansible-galaxy collection install -r requirements.yml
```

### 3. Configure Doppler

```bash
# Set Doppler project
doppler configure set project ansible-proxmox-apps
doppler configure set config prd
```

### 4. Set Environment Variables

```bash
# Export hosts from Proxmox
export CRIBL_EDGE_1="192.168.1.100"
export CRIBL_EDGE_2="192.168.1.101"
export CRIBL_STREAM="192.168.1.102"
export HAPROXY="192.168.1.103"
export SPLUNK_VM="192.168.1.104"
```

### 5. Run Playbooks

```bash
# Deploy Cribl Edge nodes
doppler run -- uv run ansible-playbook playbooks/site.yml \
  --limit cribl_edge

# Deploy HAProxy load balancer
doppler run -- uv run ansible-playbook playbooks/site.yml \
  --limit haproxy

# Deploy all applications
doppler run -- uv run ansible-playbook playbooks/site.yml
```

## Inventory

Inventory is built from environment variables. Define these in your Doppler
project:

```text
CRIBL_EDGE_1: 192.168.1.100
CRIBL_EDGE_2: 192.168.1.101
CRIBL_STREAM: 192.168.1.102
HAPROXY: 192.168.1.103
SPLUNK_VM: 192.168.1.104
```

Override locally with `doppler secrets download --no-file` or environment
variables.

## Port Assignments

| Application | Protocol | Port Range | Nodes | Purpose |
| --- | --- | --- | --- | --- |
| Syslog Input | UDP/TCP | 1514-1518 | Cribl Edge | Log ingestion |
| Syslog HEC | TCP | 8088 | Cribl Edge | Splunk HEC output |
| HAProxy Frontend | UDP/TCP | 1514-1518 | HAProxy | Load balance input |
| HAProxy Stats | TCP | 8404 | HAProxy | Admin interface |

## Roles

### cribl_edge

Deploy Cribl Edge log processor with syslog listeners and Splunk HEC output.

- Installs Cribl Edge from official package repository
- Configures UDP/TCP syslog listeners (ports 1514-1518)
- Configures Splunk HEC output
- Mounts 100GB persistent queue disk at `/opt/cribl/data`

See `roles/cribl_edge/README.md` for detailed configuration.

### cribl_stream

Deploy Cribl Stream as central processing node in the pipeline.

- Installs Cribl Stream from official packages
- Configures as processing node (not leader)
- Mounts 100GB persistent queue disk at `/opt/cribl/data`

See `roles/cribl_stream/README.md` for configuration options.

### haproxy_syslog

Deploy HAProxy configured for syslog load balancing.

- Installs HAProxy and configures syslog frontend
- Frontend: UDP/TCP ports 1514-1518
- Backend: Cribl Edge nodes (cribl-edge-01, cribl-edge-02)
- Health checks on TCP port 1514
- Syslog statistics available on port 8404

See `roles/haproxy_syslog/README.md` for customization.

## Architecture

```text
┌──────────────────┐
│  Syslog Sources  │
└────────┬─────────┘
         │
    (UDP/TCP 1514-1518)
         │
         ▼
┌──────────────────┐
│     HAProxy      │
│  Load Balancer   │
└────────┬─────────┘
         │
         ├─────────────────┬──────────────────┐
         │                 │                  │
         ▼                 ▼                  ▼
    ┌─────────┐      ┌─────────┐       ┌──────────┐
    │Cribl    │      │Cribl    │       │Cribl     │
    │Edge 01  │      │Edge 02  │       │Stream    │
    └────┬────┘      └────┬────┘       └────┬─────┘
         │                │                 │
         └────────────────┼─────────────────┘
                          │
                    (Splunk HEC)
                          │
                          ▼
                   ┌──────────────┐
                   │    Splunk    │
                   │      VM      │
                   └──────────────┘
```

## File Layout

```text
ansible-proxmox-apps/
├── README.md                    This file
├── CLAUDE.md                    AI agent documentation
├── ansible.cfg                  Ansible configuration
├── requirements.yml             Ansible Galaxy dependencies
├── .ansible-lint                Linting rules
├── .gitignore                   Git ignore rules
├── .pre-commit-config.yaml      Pre-commit hooks
├── inventory/
│   ├── hosts.yml                Dynamic inventory from env vars
│   └── group_vars/
│       └── all.yml              Global variables
├── playbooks/
│   └── site.yml                 Main playbook (all roles)
└── roles/
    ├── cribl_edge/
    │   ├── README.md
    │   ├── defaults/main.yml
    │   ├── tasks/main.yml
    │   ├── handlers/main.yml
    │   └── templates/
    ├── cribl_stream/
    │   ├── README.md
    │   ├── defaults/main.yml
    │   ├── tasks/main.yml
    │   ├── handlers/main.yml
    │   └── templates/
    └── haproxy_syslog/
        ├── README.md
        ├── defaults/main.yml
        ├── tasks/main.yml
        ├── handlers/main.yml
        └── templates/
            └── haproxy.cfg.j2
```

## Requirements

See `requirements.yml` for Ansible Galaxy collection dependencies.

Run the following to install:

```bash
uv run ansible-galaxy collection install -r requirements.yml
```

## Linting

Validate code quality with ansible-lint:

```bash
uv run ansible-lint
```

Fix common issues automatically:

```bash
uv run ansible-lint --fix
```

## Contributing

1. Update inventories in `inventory/`
2. Modify roles in `roles/*/`
3. Test with `--check --diff` mode
4. Validate with `ansible-lint`
5. Run playbook to apply

## License

MIT
