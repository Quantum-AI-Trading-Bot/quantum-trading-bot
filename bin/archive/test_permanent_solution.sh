#!/bin/bash
#
# Test and Validation Script for Permanent IB Gateway Solution
# Validates all components of the enhanced setup
#

set -euo pipefail

# Configuration
LOG_FILE="/home/davidsanker/platform/logs/permanent-solution-test.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Test results counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"

    log "🧪 Testing: $test_name"

    if eval "$test_command" >>"$LOG_FILE" 2>&1; then
        log "✅ PASS: $test_name"
        ((TESTS_PASSED++))
        return 0
    else
        log "❌ FAIL: $test_name"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Main test suite
main() {
    log "🚀 Starting Permanent IB Gateway Solution Test Suite"
    log "======================================================"

    # Test 1: VNC Server
    run_test "VNC Server Status" "pgrep -f 'Xvnc :1'"

    # Test 2: Display Environment
    run_test "X11 Display Environment" "export DISPLAY=:1 && xdpyinfo >/dev/null 2>&1"

    # Test 3: Enhanced Script Exists
    run_test "Enhanced IB Gateway Script" "test -x /home/davidsanker/platform/bin/permanent_ib_gateway.sh"

    # Test 4: Configuration File
    run_test "Enhanced IBC Configuration" "grep -q 'Enhanced Authentication Configuration' /home/davidsanker/IBC/config.ini"

    # Test 5: Authentication Script
    run_test "Daily Authentication Script" "test -x /home/davidsanker/platform/bin/daily_auth_automation.sh"

    # Test 6: Python Dependencies
    run_test "Python IB Library" "python3 -c 'import ib_insync; print(\"OK\")'"

    # Test 7: GUI Automation Tools
    run_test "xdotool Installation" "command -v xdotool"

    # Test 8: Cron Jobs
    run_test "Cron Automation Setup" "crontab -l | grep -q 'daily_auth_automation.sh'"

    # Test 9: Log Directory
    run_test "Log Directory Setup" "test -d /home/davidsanker/platform/logs/ib-gateway"

    # Test 10: Memory Configuration
    run_test "Enhanced Memory Settings" "grep -q 'Xmx4096m' /home/davidsanker/platform/bin/permanent_ib_gateway.sh"

    # Summary
    log "======================================================"
    log "📊 TEST RESULTS:"
    log "✅ Tests Passed: $TESTS_PASSED"
    log "❌ Tests Failed: $TESTS_FAILED"
    log "📈 Success Rate: $(( TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED) ))%"

    if [ $TESTS_FAILED -eq 0 ]; then
        log "🎉 ALL TESTS PASSED! The permanent solution is ready for deployment."
        log ""
        log "🚀 Next Steps:"
        log "1. Run: /home/davidsanker/platform/bin/permanent_ib_gateway.sh start"
        log "2. Monitor: tail -f /home/davidsanker/platform/logs/ib-gateway/enhanced-startup.log"
        log "3. Verify API: python3 -c 'from ib_insync import IB; ib=IB(); ib.connect(\"127.0.0.1\",4002,9999); print(\"Connected!\"); ib.disconnect()'"
        return 0
    else
        log "⚠️  Some tests failed. Please review the logs and fix issues before deployment."
        return 1
    fi
}

# Execute main function
main "$@"