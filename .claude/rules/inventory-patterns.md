---
name: inventory-patterns
description: Terraform-driven inventory consumption
---

# Inventory Patterns

## Principle

Inventory is loaded dynamically from terraform state via
`inventory/terraform_inventory.json`. The `load_terraform.yml` playbook
must run before all other playbooks.

## Data Structure

The terraform_inventory.json contains:

```json
{
  "containers": { ... },
  "vms": { ... },
  "splunk_vm": { ... },
  "docker_vms": { ... },
  "constants": {
    "service_ports": {
      "ssh": 22,
      "splunk_web": 8000,
      "splunk_hec": 8088,
      ...
    },
    "syslog_ports": {
      "unifi": 1514,
      "paloalto": 1515,
      ...
    }
  }
}
```

## Accessing Values

### Host Information

```yaml
# IP address (no default fallback)
ansible_host: "{{ hostvars['splunk']['ansible_host'] }}"

# Hostname
hostname: "{{ hostvars['splunk']['hostname'] }}"

# VMID
vmid: "{{ hostvars['splunk']['vmid'] }}"
```

### Port Constants

```yaml
# Service ports
port: "{{ terraform_data.constants.service_ports.splunk_hec }}"

# Syslog ports (as list)
ports: "{{ terraform_data.constants.syslog_ports.values() | list }}"

# Syslog ports (as dict for iteration)
{% for name, port in terraform_data.constants.syslog_ports.items() %}
  - name: {{ name }}
    port: {{ port }}
{% endfor %}
```

## Validation

The `load_terraform.yml` playbook validates that:

1. `terraform_inventory.json` exists
2. The `constants` section is present

If validation fails, regenerate the inventory from terraform-proxmox.

## Regenerating Inventory

```bash
cd ~/git/terraform-proxmox/main
terragrunt output -json ansible_inventory > \
  ~/git/ansible-proxmox-apps/main/inventory/terraform_inventory.json
```
