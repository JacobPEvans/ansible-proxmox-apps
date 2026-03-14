#!/usr/bin/env bash
# Logging Pipeline Health Check Script
# Quick validation of all pipeline components
set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Derive IPs from terraform inventory (override with env vars if needed)
INVENTORY_FILE="${INVENTORY_FILE:-inventory/terraform_inventory.json}"

if [ ! -f "$INVENTORY_FILE" ]; then
    echo -e "${RED}ERROR: $INVENTORY_FILE not found${NC}"
    echo "Generate it with: terragrunt output -json ansible_inventory > $INVENTORY_FILE"
    exit 1
fi

HAPROXY_HOST="${HAPROXY_HOST:-$(jq -r '.containers.haproxy.ip // empty' "$INVENTORY_FILE")}"
DOCKER_HOST_IP="${DOCKER_HOST_IP:-$(jq -r '.docker_vms["docker-host"].ip // empty' "$INVENTORY_FILE")}"
SPLUNK_HOST="${SPLUNK_HOST:-$(jq -r '.splunk_vm.splunk.ip // empty' "$INVENTORY_FILE")}"

for var_name in HAPROXY_HOST DOCKER_HOST_IP SPLUNK_HOST; do
    if [ -z "${!var_name}" ]; then
        echo -e "${RED}ERROR: Could not resolve $var_name from $INVENTORY_FILE${NC}"
        echo "Override with: export $var_name=<ip>"
        exit 1
    fi
done

PASSED=0
FAILED=0
TOTAL=0

# Refactored check function to avoid eval vulnerability
# Takes a test name and command with arguments directly
check() {
    local name="$1"
    shift
    ((TOTAL++))

    if "$@" &>/dev/null; then
        echo -e "${GREEN}[PASS]${NC} $name"
        ((PASSED++))
    else
        echo -e "${RED}[FAIL]${NC} $name"
        ((FAILED++))
    fi
}

echo "============================================"
echo "LOGGING PIPELINE HEALTH CHECK"
echo "============================================"
echo ""

# HAProxy checks
echo -e "${YELLOW}HAProxy ($HAPROXY_HOST)${NC}"
check "Port 1514 (UniFi)" nc -z -w2 "$HAPROXY_HOST" 1514
check "Port 1515 (Palo Alto)" nc -z -w2 "$HAPROXY_HOST" 1515
check "Port 1516 (Cisco)" nc -z -w2 "$HAPROXY_HOST" 1516
check "Port 1517 (Linux)" nc -z -w2 "$HAPROXY_HOST" 1517
check "Port 1518 (Windows)" nc -z -w2 "$HAPROXY_HOST" 1518
check "Stats page (8404)" nc -z -w2 "$HAPROXY_HOST" 8404
echo ""

# Docker Swarm Host checks (Cribl Edge via Swarm ingress)
echo -e "${YELLOW}Docker Swarm Host ($DOCKER_HOST_IP)${NC}"
check "Syslog 1514 (UniFi)" nc -z -w2 "$DOCKER_HOST_IP" 1514
check "Syslog 1515 (Palo Alto)" nc -z -w2 "$DOCKER_HOST_IP" 1515
check "Syslog 1516 (Cisco)" nc -z -w2 "$DOCKER_HOST_IP" 1516
check "Syslog 1517 (Linux)" nc -z -w2 "$DOCKER_HOST_IP" 1517
check "Syslog 1518 (Windows)" nc -z -w2 "$DOCKER_HOST_IP" 1518
check "NetFlow 2055 (UDP)" nc -z -u -w2 "$DOCKER_HOST_IP" 2055
check "Cribl Edge API (9000)" nc -z -w2 "$DOCKER_HOST_IP" 9000
echo ""

# Splunk checks
echo -e "${YELLOW}Splunk ($SPLUNK_HOST)${NC}"
check "Web UI (8000)" nc -z -w2 "$SPLUNK_HOST" 8000
check "HEC endpoint (8088)" nc -z -w2 "$SPLUNK_HOST" 8088
check "HEC health" curl -sf -k "https://$SPLUNK_HOST:8088/services/collector/health"
echo ""

# Summary
echo "============================================"
echo "RESULTS"
echo "============================================"
echo "Passed: $PASSED / $TOTAL"
echo "Failed: $FAILED / $TOTAL"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}HEALTH CHECK FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}HEALTH CHECK PASSED${NC}"
    exit 0
fi
