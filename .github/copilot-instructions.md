# GitHub Copilot Instructions — ansible-proxmox-apps

## Repository Purpose

Ansible playbooks and roles for configuring applications on Proxmox VMs/containers.
Manages: Cribl Edge, Cribl Stream, HAProxy, Technitium DNS, apt-cacher-ng, Mailpit, ntfy.
Does NOT manage Splunk (see ansible-splunk repo).

## Build & Validate

```bash
ansible-lint                    # lint all playbooks/roles
yamllint .                     # YAML formatting
molecule test                  # role integration tests (where available)
```

CI (`Ansible Lint` workflow) runs ansible-lint on all PRs. Fix all errors before merging.

## Ansible Conventions

- **Fully qualified collection names required** — always use fully qualified collection names:
  - `ansible.builtin.copy` not `copy`
  - `ansible.builtin.template` not `template`
  - `community.general.ini_file` not `ini_file`
- **Idempotency** — all tasks must be idempotent (safe to run multiple times)
- **No bare variables** — quote variables: `"{{ variable }}"` not `{{ variable }}`
- **Tags** — add meaningful tags to tasks and plays

## Role Structure

```text
roles/<name>/
  tasks/main.yml       # main task file
  handlers/main.yml    # handlers (restart services etc.)
  defaults/main.yml    # default variable values
  vars/main.yml        # role-specific variables
  templates/           # Jinja2 templates
  files/               # static files
```

## Secrets & Inventory

- Secrets via Doppler (environment variables at runtime)
- Inventory in `inventory/` — hosts organized by service group
- Service ports documented in `docs/` and CLAUDE.md

## Common Patterns

```yaml
- name: Copy configuration file
  ansible.builtin.template:
    src: config.j2
    dest: /etc/service/config.yml
    owner: root
    group: root
    mode: '0644'
  notify: Restart service
```
