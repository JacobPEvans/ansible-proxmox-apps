# Pipeline Testing Documentation

## Pipeline Architecture

```text
Syslog Sources --> HAProxy --> Docker Swarm (Cribl Edge/Stream) --> Splunk HEC
                  (LB)        (Processing)                        (Indexing)
```

- **Syslog Sources**: Network devices, hosts, and applications sending syslog
- **HAProxy**: Load balances syslog across Cribl Edge replicas
- **Docker Swarm**: Runs Cribl Edge (ingestion) and Cribl Stream (processing)
- **Splunk HEC**: Receives processed events via HTTP Event Collector

## IP and Port Convention

This repository never hardcodes IPs or ports. All values come from
terraform-managed inventory.

### IP Addresses

IPs are derived from terraform inventory and accessed via `hostvars`:

```yaml
# In playbooks and roles
splunk_host: "{{ hostvars['splunk']['ansible_host'] }}"
haproxy_host: "{{ hostvars['haproxy']['ansible_host'] }}"
```

### Port Constants

Ports are defined in `terraform_data.constants` and loaded via
`inventory/load_terraform.yml`:

```yaml
# Service ports
splunk_hec_port: "{{ terraform_data.constants.service_ports.splunk_hec }}"
splunk_web_port: "{{ terraform_data.constants.service_ports.splunk_web }}"

# Syslog ports (all assigned ports as a list)
syslog_ports: "{{ terraform_data.constants.syslog_ports.values() | list }}"

# Syslog ports (by source name)
unifi_port: "{{ terraform_data.constants.syslog_ports.unifi }}"
```

### Source of Truth

The `terraform-proxmox` repository defines all port assignments and IP
derivation logic. To view or change values, update `locals.tf` in that
repository and regenerate the inventory:

```bash
cd ~/git/terraform-proxmox/main
terragrunt output -json ansible_inventory > \
  ~/git/ansible-proxmox-apps/main/inventory/terraform_inventory.json
```

## Automated Testing

### validate-pipeline.yml -- E2E Data Flow

Validates the full pipeline by sending a test syslog message and confirming
it arrives in Splunk.

```bash
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml
```

The playbook runs these validation stages:

1. **HAProxy** -- service running, config valid, syslog ports listening
2. **Cribl Edge** -- container running, syslog listener active
3. **Splunk** -- container running, HEC endpoint healthy
4. **Docker Swarm** -- Edge and Stream replicas at expected count
5. **E2E test** -- sends a tagged syslog event and queries Splunk to confirm arrival

Run individual stages with tags:

```bash
# HAProxy only
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml --tags haproxy

# Splunk only
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml --tags splunk

# E2E data flow only
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml --tags e2e
```

Available tags: `haproxy`, `cribl_edge`, `splunk`, `cribl_docker_stack`,
`swarm`, `e2e`, `data_validation`, `validation`, `summary`.

### debug-pipeline.yml -- Hop-by-Hop Diagnostics

Diagnoses connectivity issues at each pipeline hop. Each hop isolates a
specific link in the chain:

| Hop | What It Tests |
| --- | --- |
| hop1 | HAProxy listeners accepting connections |
| hop2 | HAProxy backend health and connectivity |
| hop3 | Cribl Edge syslog listener responsiveness |
| hop4 | Cribl Edge to Cribl Stream forwarding |
| hop5 | Cribl Stream to Splunk HEC connectivity |
| hop6 | Splunk HEC endpoint health and token validity |
| summary | Aggregated pass/fail report |

```bash
# Full diagnostic
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/debug-pipeline.yml

# Single hop
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/debug-pipeline.yml --tags hop3
```

### Required Environment Variables

Both playbooks require secrets injected via Doppler:

| Variable | Purpose |
| --- | --- |
| `SPLUNK_PASSWORD` | Splunk admin password for search API queries |
| `SPLUNK_HEC_TOKEN` | HEC token for event submission |

## Manual Quick Tests

For ad-hoc verification, use variable-based commands. Retrieve actual
values from terraform inventory or Doppler before running.

### Resolve IPs from Inventory

```bash
# These are examples -- actual IPs come from hostvars
HAPROXY_IP=$(doppler run -- uv run ansible-inventory \
  -i inventory/hosts.yml --host haproxy | jq -r '.ansible_host')

DOCKER_HOST_IP=$(doppler run -- uv run ansible-inventory \
  -i inventory/hosts.yml --host cribl-docker | jq -r '.ansible_host')

SPLUNK_IP=$(doppler run -- uv run ansible-inventory \
  -i inventory/hosts.yml --host splunk | jq -r '.ansible_host')
```

### HAProxy

```bash
# Check HAProxy stats page (port from terraform_data.constants.service_ports)
curl -s http://$HAPROXY_IP:$HAPROXY_STATS_PORT/stats
```

### Cribl

```bash
# Check Cribl Edge health API
curl -s http://$DOCKER_HOST_IP:$CRIBL_EDGE_API_PORT/api/v1/health

# Check Cribl Stream health API
curl -s http://$DOCKER_HOST_IP:$CRIBL_STREAM_API_PORT/api/v1/health
```

### Splunk HEC

```bash
# Test HEC health
curl -sk https://$SPLUNK_IP:$SPLUNK_HEC_PORT/services/collector/health

# Send test event
curl -sk https://$SPLUNK_IP:$SPLUNK_HEC_PORT/services/collector/event \
  -H "Authorization: Splunk $SPLUNK_HEC_TOKEN" \
  -d '{"event": "manual-test", "sourcetype": "test", "index": "main"}'
```

Port values (`$SPLUNK_HEC_PORT`, `$HAPROXY_STATS_PORT`, etc.) are defined
in `terraform_data.constants.service_ports`. Look them up via:

```bash
jq '.constants.service_ports' inventory/terraform_inventory.json
```

## Configuring Syslog Sources

Point syslog sources at the HAProxy IP. Each source type uses a dedicated
port defined in `terraform_data.constants.syslog_ports`.

To view port assignments:

```bash
jq '.constants.syslog_ports' inventory/terraform_inventory.json
```

The `terraform-proxmox` repository maintains the authoritative port
assignment table in `locals.tf`. HAProxy routes each port to the Cribl
Edge backend using round-robin with health checks.

General configuration pattern for any syslog source:

1. Look up the assigned port for the source type in `terraform_data.constants.syslog_ports`
2. Configure the source to send syslog (UDP or TCP) to `$HAPROXY_IP:$ASSIGNED_PORT`
3. Verify events arrive using the `validate-pipeline.yml` playbook

## Troubleshooting

### No Events in Splunk

Run `debug-pipeline.yml` to isolate the failing hop. Start from hop1
and work forward:

```bash
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/debug-pipeline.yml --tags hop1,hop2,hop3
```

### HAProxy Backend Down

- Check the HAProxy stats page for backend status
- Verify Docker Swarm services: `docker service ls`
- Confirm Cribl Edge containers are healthy

### Cribl Not Receiving Events

- Verify Cribl Edge syslog listeners are configured and bound
- Check Docker Swarm service status: `docker service ps cribl_cribl-edge`
- Review Cribl Edge logs: `docker service logs cribl_cribl-edge`
- Confirm network connectivity between HAProxy and Docker host

### Splunk Not Receiving Events

- Test HEC health endpoint directly on the Splunk host
- Verify the HEC token matches the value in Doppler
- Check Splunk container health: `docker inspect splunk --format '{{.State.Health.Status}}'`
- Review Splunk container logs: `docker logs splunk`

## Verification Checklist

- [ ] HAProxy listening on all syslog ports
- [ ] HAProxy stats page accessible
- [ ] Docker Swarm cluster healthy
- [ ] Cribl Edge replicas at expected count
- [ ] Cribl Stream replicas at expected count
- [ ] Splunk container running and healthy
- [ ] Splunk HEC endpoint responding
- [ ] E2E test event visible in Splunk index
