# Splunk Docker Deployment - Lessons Learned

## Environment Variables Required

As of late 2025, the Splunk Docker image requires additional environment variables:

```yaml
environment:
  SPLUNK_START_ARGS: "--accept-license"
  SPLUNK_GENERAL_TERMS: "--accept-sgt-current-at-splunk-com"
  SPLUNK_PASSWORD: "${SPLUNK_ADMIN_PASSWORD}"
  SPLUNK_HEC_TOKEN: "${SPLUNK_HEC_TOKEN}"
```

**Note:** Use `SPLUNK_ADMIN_PASSWORD` (not `SPLUNK_PASSWORD`) to match the
variable naming convention used by terraform-proxmox packer templates and
ansible-splunk.

Without `SPLUNK_GENERAL_TERMS`, the container will fail with:

```text
License not accepted, please adjust SPLUNK_GENERAL_TERMS and/or SPLUNK_START_ARGS
```

## Native Splunk Conflicts

If deploying Docker Splunk on a host that had native Splunk:

1. Stop the native Splunk service first
2. Move or remove the old `/opt/splunk` directory
3. The Docker container will fail if port 8000 or 8088 is in use

```bash
# Stop native Splunk
sudo /opt/splunk/bin/splunk stop

# Move old data
sudo mv /opt/splunk /opt/splunk.old

# Create fresh directories
sudo mkdir -p /opt/splunk/var /opt/splunk/etc
```

## Slow Startup (chown Issue)

The Splunk Docker container runs an Ansible playbook internally that changes
file ownership. If mounting volumes with existing files, this can take 10+
minutes.

Symptoms:

- Container stuck at "change_splunk_directory_owner" in logs
- Container shows "(health: starting)" for extended periods
- High CPU usage from `AnsiballZ_file.py` process

Solutions:

1. Start with empty data directories
2. Wait longer for initial startup
3. Use named volumes instead of bind mounts

## Docker Repository Setup

The Ansible role installs Docker from the official repository:

1. Adds Docker GPG key to `/etc/apt/keyrings/docker.asc`
2. Adds Docker repo for Debian
3. Installs `docker-ce`, `docker-compose-plugin`, etc.

Debian's `docker.io` package does NOT include `docker-compose-plugin`.

## Health Check

The container uses a health check against port 8089 (management port):

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "-k", "https://localhost:8089/services/server/health"]
  interval: 30s
  timeout: 10s
  retries: 5
  start_period: 120s
```

Note: Port 8089 may not be ready until several minutes after 8000 (web UI).

## Testing HEC

After Splunk is healthy:

```bash
curl -k -X POST https://localhost:8088/services/collector/event \
  -H "Authorization: Splunk ${HEC_TOKEN}" \
  -d '{"event": "test", "sourcetype": "test", "index": "main"}'
```

## Indexes Configuration

The `indexes.conf` file is mounted read-only:

```yaml
volumes:
  - /opt/splunk-config/indexes.conf:/opt/splunk/etc/system/local/indexes.conf:ro
```

This creates the `unifi` index with:

- 100GB max size
- 90-day retention
