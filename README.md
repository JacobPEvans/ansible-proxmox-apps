# Ansible Proxmox Apps

Configure applications running on Proxmox VMs and containers.

This repository manages application deployment and configuration on virtual
machines and containers provisioned by Proxmox VE. For Proxmox infrastructure
provisioning, see `terraform-proxmox`.

## Purpose and Scope

Deploy and configure the following application stacks:

- **Cribl Docker Stack**: Cribl Edge + Stream on Docker Swarm (syslog ingestion and processing)
- **Technitium DNS**: Internal DNS server (LXC container)
- **apt-cacher-ng**: Apt proxy cache (LXC container)

All applications run on Proxmox VMs or LXC containers provisioned by
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
# Install Ansible via pipx (recommended)
pipx install ansible

# Install required collections
~/.local/pipx/venvs/ansible/bin/ansible-galaxy collection install -r requirements.yml
```

### 3. Configure Doppler

```bash
# Set Doppler project
doppler configure set project ansible-proxmox-apps
doppler configure set config prd
```

### 4. Generate Terraform Inventory

```bash
# From terraform-proxmox repo
terragrunt output -json ansible_inventory > \
  ~/git/ansible-proxmox-apps/main/inventory/terraform_inventory.json
```

### 5. Run Playbooks

```bash
# Deploy all applications
doppler run -- uv run ansible-playbook -i inventory/hosts.yml playbooks/site.yml

# Deploy with SOPS secrets overlay
sops exec-env secrets.enc.yaml 'doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/site.yml'
```

## Inventory

Inventory is loaded dynamically from `terraform_inventory.json` via
`inventory/load_terraform.yml`. See `CLAUDE.md` for full details on
environment variables and inventory groups.

## Port Assignments

| Application | Protocol | Port Range | Purpose |
| --- | --- | --- | --- |
| Syslog Input | UDP/TCP | 1514-1518 | Log ingestion (Docker Swarm ingress LB) |
| Cribl Edge API | TCP | 9000 | Cribl Edge web UI |
| Cribl Stream API | TCP | 9100 | Cribl Stream web UI |
| Splunk HEC | TCP | 8088 | Splunk HEC output |

## Roles

### cribl_docker_stack

Deploy Cribl Edge and Stream on Docker Swarm.

- Initializes Docker Swarm on the host VM
- Deploys Cribl Edge (2 replicas) and Cribl Stream (1 replica) as Swarm services
- Configures syslog inputs (ports 1514-1518 UDP/TCP) via Swarm ingress load balancing
- Configures Splunk HEC output to forward processed logs

### technitium_dns

Configure Technitium DNS with internal A records via the API.

### apt_cacher_ng

Deploy apt-cacher-ng as an apt proxy for LXC containers.

## Architecture

```text
┌──────────────────┐
│  Syslog Sources  │
└────────┬─────────┘
         │
    (UDP/TCP 1514-1518)
         │
         ▼
┌──────────────────────────────┐
│     Docker Swarm Host        │
│  ┌──────────┐ ┌──────────┐  │
│  │Cribl Edge│ │Cribl Edge│  │  (2 replicas, Swarm ingress LB)
│  │replica 1 │ │replica 2 │  │
│  └────┬─────┘ └────┬─────┘  │
│       └──────┬──────┘        │
│         ┌────▼────┐          │
│         │ Cribl   │          │
│         │ Stream  │          │
│         └────┬────┘          │
└──────────────┼───────────────┘
               │
          (Splunk HEC)
               │
               ▼
        ┌──────────────┐
        │    Splunk    │
        │  Enterprise  │
        └──────────────┘
```

## File Layout

```text
ansible-proxmox-apps/
├── README.md                    This file
├── CLAUDE.md                    AI agent documentation
├── ansible.cfg                  Ansible configuration
├── requirements.yml             Ansible Galaxy dependencies
├── secrets.enc.yaml.example     SOPS secrets template
├── inventory/
│   ├── hosts.yml                Static inventory skeleton
│   ├── load_terraform.yml       Terraform inventory loader
│   └── group_vars/
│       └── all.yml              Global variables
├── playbooks/
│   ├── site.yml                 Main deployment playbook
│   └── validate-pipeline.yml    Pipeline health checks
└── roles/
    ├── cribl_docker_stack/      Cribl Edge + Stream on Docker Swarm
    ├── technitium_dns/          Internal DNS configuration
    └── apt_cacher_ng/           Apt proxy cache
```

## Requirements

See `requirements.yml` for Ansible Galaxy collection dependencies.

Run the following to install:

```bash
~/.local/pipx/venvs/ansible/bin/ansible-galaxy collection install -r requirements.yml
```

## Linting

Validate code quality with ansible-lint:

```bash
~/.local/pipx/venvs/ansible/bin/ansible-lint
```

Fix common issues automatically:

```bash
~/.local/pipx/venvs/ansible/bin/ansible-lint --fix
```

## Contributing

1. Update inventories in `inventory/`
2. Modify roles in `roles/*/`
3. Test with `--check --diff` mode
4. Validate with `ansible-lint`
5. Run playbook to apply

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.
