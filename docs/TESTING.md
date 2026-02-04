# Testing the Logging Pipeline

This document describes how to test the syslog logging pipeline from sources
through HAProxy, Cribl, and into Splunk.

## Pipeline Architecture (Target End State)

```text
┌────────────────┐    ┌─────────────┐    ┌─────────────────┐    ┌────────┐
│ Syslog Sources │───▶│   HAProxy   │───▶│  Docker Swarm   │───▶│ Splunk │
│                │    │ (Load Bal.) │    │ (Cribl E/S)     │    │  HEC   │
└────────────────┘    └─────────────┘    └─────────────────┘    └────────┘
     :1514                :1514               :1514                :8088
```

HAProxy is the target entry point for all syslog traffic. It may be temporarily
bypassed for debugging, but production traffic flows through HAProxy.

## IP Address Convention

**Git-committed files use placeholder IPs**: `192.168.0.*`

Real IPs are derived at runtime:

- Gateway prefix from `PROXMOX_VE_GATEWAY` environment variable
- Last octet equals VMID (e.g., VMID 175 → `x.x.x.175`)

| Component    | VMID | Placeholder IP  | Real IP Formula         |
| ------------ | ---- | --------------- | ----------------------- |
| HAProxy      | 175  | 192.168.0.175   | `${GATEWAY_PREFIX}.175` |
| Docker Swarm | 250  | 192.168.0.250   | `${GATEWAY_PREFIX}.250` |
| Splunk       | 200  | 192.168.0.200   | `${GATEWAY_PREFIX}.200` |

## Port Assignments

| Port | Protocol | Service         | Component        |
| ---- | -------- | --------------- | ---------------- |
| 1514 | TCP/UDP  | UniFi syslog    | HAProxy → Cribl  |
| 1515 | TCP/UDP  | Palo Alto       | HAProxy → Cribl  |
| 1516 | TCP/UDP  | Cisco ASA       | HAProxy → Cribl  |
| 1517 | TCP/UDP  | Linux/macOS     | HAProxy → Cribl  |
| 1518 | TCP/UDP  | Windows         | HAProxy → Cribl  |
| 2055 | UDP      | NetFlow         | Future           |
| 8088 | TCP      | Splunk HEC      | Cribl → Splunk   |
| 8404 | TCP      | HAProxy Stats   | Admin interface  |
| 9000 | TCP      | Cribl Edge UI   | Web interface    |
| 9100 | TCP      | Cribl Stream UI | Web interface    |

## Automated Testing

### Debug Pipeline (Hop-by-Hop Diagnostics)

The `debug-pipeline.yml` playbook tests each hop in the pipeline:

```bash
# Run full debug (all hops)
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/debug-pipeline.yml

# Run specific hop
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/debug-pipeline.yml --tags hop1
```

**Hop Tags:**

| Tag       | Tests                                              |
| --------- | -------------------------------------------------- |
| `hop1`    | HAProxy listening (ports 1514-1518, 8404)          |
| `hop2`    | HAProxy → Docker Swarm backend connectivity        |
| `hop3`    | Cribl Docker service health (Swarm state, replicas)|
| `hop4`    | Cribl API health (Edge, Stream, syslog port)       |
| `hop5`    | Cribl → Splunk HEC connectivity                    |
| `hop6`    | Splunk HEC listener (container, ports, health)     |
| `summary` | Full pipeline summary                              |

### E2E Validation (Data Flow Test)

The `validate-pipeline.yml` playbook sends a test event and verifies it arrives
in Splunk:

```bash
# Run E2E test
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml --tags e2e

# Run all validation
doppler run -- uv run ansible-playbook \
  -i inventory/hosts.yml playbooks/validate-pipeline.yml
```

Required environment variables (via Doppler):

- `SPLUNK_ADMIN_PASSWORD` - Splunk admin password for search API

## Manual Quick Tests

Replace placeholder IPs with your real IPs before running.

### HAProxy Tests

```bash
# Test HAProxy syslog listening
nc -zv 192.168.0.175 1514

# Test HAProxy stats page
curl -s http://192.168.0.175:8404/stats

# Send test syslog message through HAProxy
echo "<14>$(date --iso-8601=seconds) test-host manual-test: Hello" | \
  nc -u -w1 192.168.0.175 1514
```

### Cribl Tests

```bash
# Test Cribl Edge health
curl -s http://192.168.0.250:9000/api/v1/health

# Test Cribl Stream health
curl -s http://192.168.0.250:9100/api/v1/health

# Test syslog port directly on Docker host
nc -zv 192.168.0.250 1514
```

### Splunk HEC Tests

```bash
# Test HEC health endpoint (HTTPS required, -k skips cert verify)
curl -sk https://192.168.0.200:8088/services/collector/health

# Send test event to HEC (requires token)
curl -k https://192.168.0.200:8088/services/collector/event \
  -H "Authorization: Splunk ${SPLUNK_HEC_TOKEN}" \
  -d '{"event": "test from CLI", "sourcetype": "test", "index": "main"}'
```

## Configuring Syslog Sources

### UniFi (Port 1514)

1. UniFi Controller → Settings → System → Remote Syslog
2. Server: Your HAProxy IP (VMID 175)
3. Port: 1514
4. Protocol: UDP

### Linux (Port 1517)

Create `/etc/rsyslog.d/90-remote.conf`:

```text
# Forward all logs to logging pipeline
*.* @192.168.0.175:1517
```

Restart rsyslog:

```bash
sudo systemctl restart rsyslog
```

### macOS (Port 1517)

macOS uses unified logging with ASL (Apple System Log). To forward to remote
syslog:

1. Create `/etc/syslog.conf` with remote server configuration
2. Configure the remote server IP (HAProxy, VMID 175)
3. Port: 1517

Note: macOS unified logging requires additional configuration. See Apple
documentation for current best practices on log forwarding.

### Windows (Port 1518)

Use a syslog agent such as:

- NXLog (recommended)
- Snare
- Windows Event Forwarding with a syslog bridge

Configure the agent to send to your HAProxy IP (VMID 175) on port 1518.

## Troubleshooting

### No Events in Splunk

1. **Check HAProxy**: Run `--tags hop1` to verify HAProxy is listening
2. **Check backend**: Run `--tags hop2` to verify Docker Swarm connectivity
3. **Check Cribl**: Run `--tags hop3,hop4` to verify Cribl services
4. **Check Splunk**: Run `--tags hop6` to verify HEC is healthy

### HAProxy Backend Down

Check HAProxy stats page at `http://<haproxy-ip>:8404/stats` for backend
health.

Common issues:

- Docker Swarm not initialized
- Cribl containers not running
- Firewall blocking traffic

### Cribl Not Receiving Logs

1. Verify syslog listener is configured in Cribl UI
2. Check Docker service replicas: `docker service ls`
3. Verify network connectivity: `nc -zv <docker-host> 1514`

### Splunk Not Receiving Events

1. Verify HEC is enabled in Splunk
2. Check HEC token is correct in Cribl output configuration
3. Verify Splunk container is running: `docker ps | grep splunk`
4. Check HEC health: `curl -sk https://<splunk-ip>:8088/services/collector/health`

## Verification Checklist

Before considering the pipeline operational:

- [ ] HAProxy listening on ports 1514-1518
- [ ] HAProxy stats page accessible on 8404
- [ ] Docker Swarm active with healthy nodes
- [ ] Cribl Edge replicas running (2/2)
- [ ] Cribl Stream replica running (1/1)
- [ ] Cribl Edge API healthy (port 9000)
- [ ] Cribl Stream API healthy (port 9100)
- [ ] Splunk container running
- [ ] Splunk HEC healthy (port 8088)
- [ ] E2E test event visible in Splunk
