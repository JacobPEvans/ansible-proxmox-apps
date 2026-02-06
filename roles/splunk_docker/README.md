# Splunk Docker Role

Installs Docker and deploys Splunk Enterprise as a container with HEC enabled.

## Requirements

- Debian-based OS with apt
- Doppler secrets for SPLUNK_ADMIN_PASSWORD and SPLUNK_HEC_TOKEN

## Role Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `splunk_docker_image` | `splunk/splunk:latest` | Splunk Docker image |
| `splunk_docker_password` | (from Doppler) | Splunk admin password |
| `splunk_docker_hec_token` | (from Doppler) | HEC authentication token |
| `splunk_docker_web_port` | `8000` | Splunk Web UI port |
| `splunk_docker_hec_port` | `8088` | Splunk HEC port |
| `splunk_docker_data_dir` | `/opt/splunk` | Persistent data directory |
| `splunk_docker_indexes` | `[{name: unifi, ...}]` | Indexes to create |
| `splunk_docker_firewall_enabled` | `true` | Apply iptables lockdown |

## Example Playbook

```yaml
- name: Deploy Splunk Docker
  hosts: splunk
  roles:
    - splunk_docker
```

## Security

This role applies iptables rules to:

- Block all outbound internet traffic
- Allow only RFC1918 (private) inbound traffic
- Require development license (no phone-home)

## Dependencies

- community.docker collection
