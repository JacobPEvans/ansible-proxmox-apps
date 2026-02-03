# Testing Framework

Comprehensive testing documentation for the ansible-proxmox-apps repository.

## Testing Requirements

**All changes MUST be tested before commits and PRs.** This is non-negotiable.

### Pre-Commit Checklist

1. **Lint validation**: `uv run ansible-lint`
2. **Syntax check**: `doppler run -- uv run ansible-playbook --syntax-check`
3. **Dry run**: `doppler run -- uv run ansible-playbook --check --diff`
4. **Pipeline validation**: Run appropriate test playbook

## Pipeline Architecture

Target architecture with HAProxy in the pipeline:

```text
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐    ┌──────────┐
│ Syslog      │───▶│   HAProxy   │───▶│ Docker Swarm    │───▶│  Splunk  │
│ Sources     │    │   (LB)      │    │ (Cribl Edge)    │    │  (HEC)   │
└─────────────┘    └─────────────┘    └─────────────────┘    └──────────┘
     :1514             :1514               :1514                :8088
```

### IP Address Convention

IPs are **never hardcoded**. They are derived from:

```text
${GATEWAY_PREFIX} = first 3 octets of PROXMOX_VE_GATEWAY
IP = ${GATEWAY_PREFIX}.{VMID}
```

| Component | VMID | IP Pattern |
| --- | --- | --- |
| HAProxy | 175 | `${GATEWAY_PREFIX}.175` |
| Splunk | 200 | `${GATEWAY_PREFIX}.200` |
| Docker Swarm | 250 | `${GATEWAY_PREFIX}.250` |

### Port Assignments

| Port | Protocol | Service | Notes |
| --- | --- | --- | --- |
| 514 | TCP/UDP | Standard syslog | HAProxy frontend |
| 1514 | TCP/UDP | UniFi syslog | Primary source |
| 1515 | TCP/UDP | Palo Alto | Future |
| 1516 | TCP/UDP | Cisco ASA | Future |
| 1517 | TCP/UDP | Linux/macOS | macOS uses same port as Linux |
| 1518 | TCP/UDP | Windows | Future |
| 2055 | UDP | NetFlow | Future |
| 8088 | TCP | Splunk HEC | Destination |
| 8404 | TCP | HAProxy Stats | Admin interface |
| 9000 | TCP | Cribl Edge UI | Web interface |
| 9100 | TCP | Cribl Stream UI | Web interface |

## Test Playbooks

### Debug Pipeline (`debug-pipeline.yml`)

**Purpose**: Hop-by-hop testing to identify failure points in the syslog pipeline.

**When to use**:

- Infrastructure deploys but no events reach Splunk
- Troubleshooting connectivity issues
- After infrastructure changes

**Usage**:

```bash
# Run all hops
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/debug-pipeline.yml

# Run specific hop
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/debug-pipeline.yml --tags hop3
```

**Tags**:

| Tag | Description |
| --- | --- |
| `hop1` | HAProxy listening tests |
| `hop2` | HAProxy → Cribl backend connectivity |
| `hop3` | Cribl Edge Docker service tests |
| `hop4` | Cribl configuration verification |
| `hop5` | Cribl → Splunk HEC connectivity |
| `hop6` | Splunk HEC listener tests |
| `summary` | Pipeline debug results summary |

### Validate Pipeline (`validate-pipeline.yml`)

**Purpose**: End-to-end validation of data flow through the pipeline.

**When to use**:

- After successful deployment
- Before marking work complete
- Periodic health checks

**Usage**:

```bash
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml
```

**Tags**:

| Tag | Description |
| --- | --- |
| `haproxy` | HAProxy service validation |
| `cribl_edge` | Cribl Edge container validation |
| `splunk` | Splunk container and HEC validation |
| `cribl_docker_stack` | Docker Swarm stack validation |
| `e2e` | End-to-end data flow test (through HAProxy) |
| `summary` | Validation summary |

## Testing Workflow

### Before Making Changes

1. Run debug playbook to establish baseline:

   ```bash
   doppler run -- uv run ansible-playbook \
     -i inventory/hosts.yml playbooks/debug-pipeline.yml
   ```

2. Save output for comparison

### After Making Changes

1. **Lint check**:

   ```bash
   uv run ansible-lint
   ```

2. **Syntax validation**:

   ```bash
   doppler run -- uv run ansible-playbook \
     -i inventory/hosts.yml playbooks/site.yml --syntax-check
   ```

3. **Dry run** (see what would change):

   ```bash
   doppler run -- uv run ansible-playbook \
     -i inventory/hosts.yml playbooks/site.yml --check --diff
   ```

4. **Apply changes**:

   ```bash
   doppler run -- uv run ansible-playbook \
     -i inventory/hosts.yml playbooks/site.yml
   ```

5. **Validate pipeline**:

   ```bash
   doppler run -- uv run ansible-playbook \
     -i inventory/hosts.yml playbooks/validate-pipeline.yml
   ```

### Troubleshooting Failures

If validation fails:

1. Run debug playbook to identify which hop is failing
2. Focus on the failing hop's output
3. Check the "Common Issues" table in the summary
4. Fix the issue
5. Re-run debug playbook to verify fix
6. Run validation playbook to confirm E2E flow

## Manual Quick Tests

For rapid troubleshooting without running full playbooks.
Replace `${GATEWAY_PREFIX}` with your network's first 3 octets.

```bash
# Test HAProxy listening (VMID 175)
nc -zv ${GATEWAY_PREFIX}.175 1514

# Test Cribl health (Docker Swarm VMID 250)
curl -s http://${GATEWAY_PREFIX}.250:9000/api/v1/health | jq .

# Test Splunk HEC (VMID 200)
curl -s https://${GATEWAY_PREFIX}.200:8088/services/collector/health -k

# Send test syslog through HAProxy
logger -n ${GATEWAY_PREFIX}.175 -P 1514 "TEST_$(date +%s)"
```

**To get your GATEWAY_PREFIX**: `echo $PROXMOX_VE_GATEWAY | cut -d. -f1-3`

## Configuring Syslog Sources

All syslog sources should target HAProxy (VMID 175) for load balancing.

### UniFi (Port 1514)

1. UniFi Controller → Settings → System → Remote Syslog
2. Server: `${GATEWAY_PREFIX}.175` (HAProxy)
3. Port: 1514
4. Protocol: UDP

### macOS (Port 1517)

macOS uses unified logging. To forward syslog events:

1. Create `/etc/syslog.conf` or use `log` command
2. Target: `${GATEWAY_PREFIX}.175` (HAProxy), port 1517
3. Protocol: UDP recommended

Example `/etc/syslog.conf`:

```text
*.* @<haproxy-ip>:1517
```

Replace `<haproxy-ip>` with your HAProxy IP (`${GATEWAY_PREFIX}.175`).

### Linux (Port 1517)

Create `/etc/rsyslog.d/90-remote.conf`:

```text
# Forward all logs to HAProxy (replace with your IP)
*.* @<haproxy-ip>:1517
```

Restart rsyslog:

```bash
sudo systemctl restart rsyslog
```

### Windows (Port 1518)

Use NXLog or Syslog-ng to forward Windows Event Logs:

1. Install NXLog CE
2. Configure output to HAProxy IP (`${GATEWAY_PREFIX}.175`), port 1518
3. Protocol: TCP recommended for reliability

## Common Issues and Solutions

| Symptom | Cause | Fix |
| --- | --- | --- |
| HAProxy not listening | Service stopped | Check systemd, config syntax |
| Backends DOWN | Cribl not up | Verify Docker service health |
| Config missing | Volume mount fail | Check docker-stack volumes |
| Can't reach Splunk | Network/firewall | Test curl from container |
| HEC rejects events | Bad token | Verify SPLUNK_HEC_TOKEN |
| Events lost | Wrong routes | Check routes.yml, outputs.yml |
| OOM killed | Memory too low | Increase docker-stack memory |

## CI/CD Integration

When creating PRs, ensure:

1. All lint checks pass
2. Syntax validation succeeds
3. Dry run shows expected changes only
4. If infrastructure changes: run debug-pipeline.yml
5. If data flow changes: run validate-pipeline.yml

## Related Documentation

- [Splunk Docker Setup](./SPLUNK_DOCKER.md)
- [Main CLAUDE.md](../CLAUDE.md) - Testing requirements
- [Inventory Structure](../inventory/) - Dynamic inventory from Terraform
