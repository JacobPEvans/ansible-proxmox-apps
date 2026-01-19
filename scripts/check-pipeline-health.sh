#!/usr/bin/env bash
# Logging Pipeline Health Check Script
# Quick validation of all pipeline components
set -euo pipefail

# Configuration (override via environment)
HAPROXY_HOST="${HAPROXY_HOST:-10.0.1.175}"
SPLUNK_HOST="${SPLUNK_HOST:-10.0.1.200}"
CRIBL_EDGE_HOSTS="${CRIBL_EDGE_HOSTS:-10.0.1.180 10.0.1.181}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0
TOTAL=0

check() {
    local name="$1"
    local cmd="$2"
    ((TOTAL++))

    if eval "$cmd" &>/dev/null; then
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
check "Port 1514 (UniFi)" "nc -z -w2 $HAPROXY_HOST 1514"
check "Port 1515 (Palo Alto)" "nc -z -w2 $HAPROXY_HOST 1515"
check "Port 1516 (Cisco)" "nc -z -w2 $HAPROXY_HOST 1516"
check "Port 1517 (Linux)" "nc -z -w2 $HAPROXY_HOST 1517"
check "Port 1518 (Windows)" "nc -z -w2 $HAPROXY_HOST 1518"
check "Stats page (8404)" "nc -z -w2 $HAPROXY_HOST 8404"
echo ""

# Cribl Edge checks
echo -e "${YELLOW}Cribl Edge Nodes${NC}"
for host in $CRIBL_EDGE_HOSTS; do
    check "Cribl Edge $host:1514" "nc -z -w2 $host 1514"
done
echo ""

# Splunk checks
echo -e "${YELLOW}Splunk ($SPLUNK_HOST)${NC}"
check "Web UI (8000)" "nc -z -w2 $SPLUNK_HOST 8000"
check "HEC endpoint (8088)" "nc -z -w2 $SPLUNK_HOST 8088"
check "HEC health" "curl -sf -k https://$SPLUNK_HOST:8088/services/collector/health"
echo ""

# Summary
echo "============================================"
echo "SUMMARY: $PASSED/$TOTAL checks passed"
echo "============================================"

if [[ $FAILED -gt 0 ]]; then
    echo -e "${RED}Pipeline has $FAILED failed checks${NC}"
    exit 1
else
    echo -e "${GREEN}Pipeline is healthy!${NC}"
    exit 0
fi
