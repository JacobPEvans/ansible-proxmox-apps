#!/usr/bin/env bash
# Logging Pipeline Health Check Script
# Quick validation of all pipeline components
set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Configuration - sourced from environment variables for flexibility
# Users can override these before running the script:
#   export HAPROXY_HOST=10.0.1.175
#   export CRIBL_EDGE_HOSTS="10.0.1.180 10.0.1.181"
#   export SPLUNK_HOST=10.0.1.200
read -r -a CRIBL_EDGE_HOSTS <<< "${CRIBL_EDGE_HOSTS:-10.0.1.180 10.0.1.181}"
HAPROXY_HOST="${HAPROXY_HOST:-10.0.1.175}"
SPLUNK_HOST="${SPLUNK_HOST:-10.0.1.200}"

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

# Cribl Edge checks - iterate over array safely
echo -e "${YELLOW}Cribl Edge Nodes${NC}"
for host in "${CRIBL_EDGE_HOSTS[@]}"; do
    check "Cribl Edge $host:1514" nc -z -w2 "$host" 1514
done
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
