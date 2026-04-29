# cribl_packs

Install Cribl `.crbl` packs onto Cribl Edge and Cribl Stream LXC containers
from public GitHub release assets.

## What it does

For each host the role detects whether it belongs to `cribl_edge` or
`cribl_stream_group` (set up by inventory loading), then installs the
corresponding pack list under the right Cribl mode directory:

- Edge LXCs (`cribl_edge` group) → `/opt/cribl/local/edge/packs/<pack-name>/`
- Stream LXCs (`cribl_stream_group`) → `/opt/cribl/local/cribl/packs/<pack-name>/`

Hosts in neither group are skipped (no-op).

## Idempotency

Each pack installation drops a sentinel file `.<version>.installed` inside the
pack directory. Re-runs on the same version skip the download. Re-runs on a
new version remove the prior pack directory, redownload, and unarchive — then
notify the appropriate `Restart cribl` handler.

## Installation

This role lives in `ansible-proxmox-apps/roles/cribl_packs/` and is referenced
directly by `playbooks/site.yml`. There is no Galaxy install step — the role
ships in this repo.

It depends on `cribl_edge` or `cribl_stream` having already installed the
Cribl binary and started the service, so run it after both in `site.yml`.

## Usage

In `playbooks/site.yml`, after the `cribl_edge` and `cribl_stream` plays:

```yaml
- name: Install Cribl packs
  hosts: cribl_edge:cribl_stream_group
  become: true
  roles:
    - cribl_packs
```

Override the pack list per inventory by setting `cribl_packs_for_edge` or
`cribl_packs_for_stream` in inventory/group_vars. See `defaults/main.yml`
for the default list (cc-edge-copilot-otel, cc-edge-vscode-io,
cc-stream-github-copilot-rest-io).

## Variables

See `defaults/main.yml` for the full list. Pin a specific version by editing
the `version:` field on the relevant pack entry.

## License

MIT (matches the parent repo).
