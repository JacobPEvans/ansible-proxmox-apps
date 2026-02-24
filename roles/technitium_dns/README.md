# Technitium DNS Role

Configures a [Technitium DNS Server](https://technitium.com/dns/) instance with
an internal DNS zone, A records for all infrastructure hosts, and CNAME aliases
for services.

## Purpose

- Creates a primary internal DNS zone (e.g. `home.lab`)
- Populates A records dynamically from the Terraform inventory
- Creates CNAME aliases for stable service entry points
- Configures upstream forwarders for external queries

## Requirements

- Technitium DNS Server must already be installed and reachable
- `TECHNITIUM_DNS_API_TOKEN` must be available (via Doppler or environment)
- `PROXMOX_DOMAIN` must be set to the internal domain name
- Ansible 2.15+

## Role Variables

See `defaults/main.yml` for all available variables:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `technitium_dns_api_url` | `http://{{ technitium_dns_host }}:5380` | Technitium API base URL |
| `technitium_dns_api_token` | `env TECHNITIUM_DNS_API_TOKEN` | API token for authentication |
| `technitium_dns_internal_domain` | `env PROXMOX_DOMAIN` | Internal DNS zone name |
| `technitium_dns_zone_type` | `Primary` | DNS zone type |
| `technitium_dns_zone_ttl` | `3600` | Default TTL for records (seconds) |
| `technitium_dns_a_records` | `[]` | A records to create (populated from inventory) |
| `technitium_dns_cname_records` | see below | CNAME aliases to create |
| `technitium_dns_forwarders` | `["8.8.8.8", "8.8.4.4"]` | Upstream DNS forwarders |
| `technitium_dns_recursion` | `true` | Enable recursive resolution |
| `technitium_dns_cache_enabled` | `true` | Enable DNS caching |
| `technitium_dns_api_timeout` | `30` | API request timeout (seconds) |

### Default CNAME Records

| Name | Target | Purpose |
| ---- | ------ | ------- |
| `cribl-edge` | `docker` | Cribl Edge API endpoint |
| `cribl-stream` | `docker` | Cribl Stream API endpoint |
| `syslog` | `haproxy` | Stable syslog entry point via HAProxy |

## Environment Variables

| Variable | Purpose | Source |
| -------- | ------- | ------ |
| `TECHNITIUM_DNS_API_TOKEN` | API token for Technitium | Doppler / SOPS |
| `PROXMOX_DOMAIN` | Internal DNS domain name | Doppler / SOPS |

## Example Playbook

```yaml
- name: Configure Technitium DNS
  hosts: technitium_dns_group
  become: false
  roles:
    - technitium_dns
```

With custom forwarders and additional CNAME records:

```yaml
- name: Configure Technitium DNS
  hosts: technitium_dns_group
  roles:
    - role: technitium_dns
      vars:
        technitium_dns_forwarders:
          - "1.1.1.1"
          - "1.0.0.1"
        technitium_dns_cname_records:
          - name: cribl-edge
            target: docker
          - name: cribl-stream
            target: docker
          - name: syslog
            target: haproxy
          - name: monitor
            target: monitoring-host
```

## Dependencies

None.

## License

Apache-2.0
