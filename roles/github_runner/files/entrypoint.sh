#!/bin/bash
set -e

# Generate a unique runner name from prefix + hostname
RUNNER_NAME="${RUNNER_NAME_PREFIX:-proxmox-runner}-${HOSTNAME}"

if [ ! -f .runner ]; then
  ./config.sh \
    --url "https://github.com/${GITHUB_REPOSITORY}" \
    --token "${RUNNER_TOKEN}" \
    --labels "${RUNNER_LABELS:-self-hosted,Linux}" \
    --name "${RUNNER_NAME}" \
    --unattended \
    --replace
fi

# Clear the registration token from the process environment after config
# completes.  The token is single-use and expires in 1h, but unsetting it
# removes it from /proc/*/environ at runtime.  Note: docker inspect still
# shows the original container env config — for that threat model, use
# Docker secrets or a file-based approach instead.
unset RUNNER_TOKEN

cleanup() {
  # Registration token was already consumed and unset. Deregistration requires
  # a fresh removal token — generate one if gh CLI is available, otherwise
  # warn the operator.
  local remove_token
  if command -v gh >/dev/null 2>&1 && [ -n "${GITHUB_REPOSITORY:-}" ]; then
    remove_token=$(gh api "repos/${GITHUB_REPOSITORY}/actions/runners/remove-token" --method POST --jq '.token' 2>/dev/null || true)
  fi
  if [ -n "${remove_token:-}" ]; then
    ./config.sh remove --token "$remove_token" 2>/dev/null || true
  else
    echo "Warning: Could not obtain a removal token; runner may need manual removal via GitHub UI."
  fi
}
trap cleanup EXIT

exec ./run.sh
