# Apt-Cacher-NG Role

Installs and configures Apt-Cacher-NG as a caching proxy for Debian/Ubuntu
package repositories.

## Purpose

Provides a local apt caching proxy to:

- Speed up package installations across multiple hosts
- Reduce bandwidth usage by caching frequently used packages
- Enable package installations on hosts without direct internet access

## Requirements

- Debian-based host (Debian 11+, Ubuntu 20.04+)
- Host must have internet access to fetch packages from upstream mirrors

## Role Variables

See `defaults/main.yml` for all available variables:

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `apt_cacher_ng_port` | `3142` | Port for proxy |
| `apt_cacher_ng_cache_dir` | `/var/cache/apt-cacher-ng` | Cache location |
| `apt_cacher_ng_passthrough_enabled` | `false` | HTTPS passthrough |
| `apt_cacher_ng_admin_enabled` | `true` | Admin web UI |

## Client Configuration

After deploying apt-cacher-ng, configure clients to use it:

```bash
# Create /etc/apt/apt.conf.d/00proxy on client machines
echo 'Acquire::http::Proxy "http://<apt-cacher-ip>:3142";' \
  | sudo tee /etc/apt/apt.conf.d/00proxy
```

Or deploy via Ansible:

```yaml
- name: Configure apt proxy on clients
  ansible.builtin.copy:
    content: 'Acquire::http::Proxy "http://<apt_cacher_ip_or_hostname>:3142";'
    dest: /etc/apt/apt.conf.d/00proxy
    mode: '0644'
```

## Example Playbook

```yaml
- name: Deploy Apt-Cacher-NG
  hosts: apt_cacher_group
  become: true
  roles:
    - apt_cacher_ng
```

## Admin Interface

Access the admin interface at:

```text
http://<apt-cacher-ip>:3142/acng-report.html
```

## Dependencies

None.

## License

Apache-2.0
