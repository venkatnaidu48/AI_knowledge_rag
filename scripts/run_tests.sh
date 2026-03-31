#!/bin/bash
# Automated Test Runner for RAG Application
# Runs all test suites and generates reports

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PYTHON_CMD=${PYTHON_CMD:-python}
TEST_DIR=${TEST_DIR:-tests}
REPORTS_DIR=${REPORTS_DIR:-test-reports}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}RAG Application - Automated Test Runner${NC}"
echo -e "${BLUE}==========================================${NC}\n"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install pytest pytest-cov pytest-asyncio pytest-html pytest-xdist pytest-timeout
fi

# ============================================================================
# UNIT TESTS
# ============================================================================

echo -e "${YELLOW}[1/4] Running Unit Tests...${NC}"

$PYTHON_CMD -m pytest "$TEST_DIR/unit" \
    -v \
    --cov=src \
    --cov-report=html:"$REPORTS_DIR/coverage_unit_$TIMESTAMP" \
    --html="$REPORTS_DIR/unit_tests_$TIMESTAMP.html" \
    --self-contained-html \
    -m "unit" \
    2>&1 | tee "$REPORTS_DIR/unit_tests_$TIMESTAMP.log" || true

echo -e "${GREEN}✓ Unit tests complete${NC}\n"

# ============================================================================
# INTEGRATION TESTS
# ============================================================================

echo -e "${YELLOW}[2/4] Running Integration Tests...${NC}"

# Start test database if available
if command -v docker &> /dev/null; then
    echo "  Starting test database containers..."
    docker-compose -f docker-compose.test.yml up -d 2>/dev/null || true
    sleep 5
fi

$PYTHON_CMD -m pytest "$TEST_DIR/integration" \
    -v \
    --cov=src \
    --cov-report=html:"$REPORTS_DIR/coverage_integration_$TIMESTAMP" \
    --html="$REPORTS_DIR/integration_tests_$TIMESTAMP.html" \
    --self-contained-html \
    -m "integration" \
    --timeout=60 \
    2>&1 | tee "$REPORTS_DIR/integration_tests_$TIMESTAMP.log" || true

# Clean up test containers
if command -v docker &> /dev/null; then
    echo "  Stopping test database containers..."
    docker-compose -f docker-compose.test.yml down 2>/dev/null || true
fi

echo -e "${GREEN}✓ Integration tests complete${NC}\n"

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

echo -e "${YELLOW}[3/4] Running Performance Tests...${NC}"

$PYTHON_CMD -m pytest "$TEST_DIR/performance" \
    -v \
    --benchmark-only \
    --html="$REPORTS_DIR/performance_tests_$TIMESTAMP.html" \
    --self-contained-html \
    -m "performance" \
    2>&1 | tee "$REPORTS_DIR/performance_tests_$TIMESTAMP.log" || true

echo -e "${GREEN}✓ Performance tests complete${NC}\n"

# ============================================================================
# COVERAGE SUMMARY
# ============================================================================

echo -e "${YELLOW}[4/4] Generating Coverage Report...${NC}"

$PYTHON_CMD -m pytest "$TEST_DIR" \
    -v \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html:"$REPORTS_DIR/coverage_combined_$TIMESTAMP" \
    --cov-report=xml:"$REPORTS_DIR/coverage_$TIMESTAMP.xml" \
    --html="$REPORTS_DIR/all_tests_$TIMESTAMP.html" \
    --self-contained-html \
    --tb=short \
    2>&1 | tee "$REPORTS_DIR/all_tests_$TIMESTAMP.log"

COVERAGE_STATUS=$?

echo -e "${GREEN}✓ Coverage report complete${NC}\n"

# ============================================================================
# GENERATE SUMMARY REPORT
# ============================================================================

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Test Summary Report${NC}"
echo -e "${BLUE}==========================================${NC}\n"

echo -e "${BLUE}Report Artifacts:${NC}"
echo "  Unit Tests:              $REPORTS_DIR/unit_tests_$TIMESTAMP.html"
echo "  Integration Tests:       $REPORTS_DIR/integration_tests_$TIMESTAMP.html"
echo "  Performance Tests:       $REPORTS_DIR/performance_tests_$TIMESTAMP.html"
echo "  Coverage Report:         $REPORTS_DIR/coverage_combined_$TIMESTAMP/index.html"
echo "  Combined Report:         $REPORTS_DIR/all_tests_$TIMESTAMP.html"
echo "  XML Report:              $REPORTS_DIR/coverage_$TIMESTAMP.xml"
echo ""

echo -e "${BLUE}Report Directory Contents:${NC}"
ls -lh "$REPORTS_DIR" | tail -n 10

echo ""

if [ $COVERAGE_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    
    # Display coverage percentage
    if grep -q "FAILED" "$REPORTS_DIR/all_tests_$TIMESTAMP.log"; then
        echo -e "${RED}⚠ Some tests failed${NC}"
        exit 1
    fi
    
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
