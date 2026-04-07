---
name: ip-addressing
description: No hardcoded values - terraform is authority
---

# IP Addressing Rule

## Principle

**terraform-proxmox is the single source of truth** for all infrastructure
constants. This repository CONSUMES values, never DEFINES them.

## Prohibited Patterns

Never use these in role defaults or tasks:

```yaml
# BAD - hardcoded IP with default
splunk_host: "{{ hostvars['splunk'].ansible_host | default('192.168.0.200') }}"

# BAD - hardcoded port
splunk_hec_port: 8088

# BAD - hardcoded port list
syslog_ports:
  - 1514
  - 1515
```

## Required Patterns

Always reference terraform_data.constants:

```yaml
# GOOD - IP from inventory only (no fallback)
splunk_host: "{{ hostvars['splunk']['ansible_host'] }}"

# GOOD - port from terraform constants
splunk_hec_port: "{{ terraform_data.constants.service_ports.splunk_hec }}"

# GOOD - port list from terraform constants
syslog_ports: "{{ terraform_data.constants.syslog_ports.values() | list }}"
```

## Updating Values

To change any port or IP:

1. Update `terraform-proxmox/main/locals.tf`
2. Run `terragrunt apply` in terraform-proxmox
3. Regenerate inventory:

   ```bash
   cd ~/git/terraform-proxmox/main
   terragrunt output -json ansible_inventory > \
     ~/git/ansible-proxmox-apps/main/inventory/terraform_inventory.json
   ```

## Documentation

Never document specific port numbers or IPs in this repository.
Document HOW to retrieve values, not the values themselves.
