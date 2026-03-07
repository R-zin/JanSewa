#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Jan Sewa - Full Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create test results directory
mkdir -p test_results

# Backend Tests
echo -e "${YELLOW}Running Backend Tests...${NC}"
cd backend
python -m pytest tests/ --tb=short -v --junit-xml=../test_results/backend_results.xml > ../test_results/backend_output.txt 2>&1
BACKEND_EXIT=$?
cd ..

if [ $BACKEND_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Backend tests completed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Backend tests completed with some failures${NC}"
fi

# Count backend test results
BACKEND_PASSED=$(grep -o "passed" test_results/backend_output.txt | wc -l | tr -d ' ')
BACKEND_FAILED=$(grep -o "failed" test_results/backend_output.txt | wc -l | tr -d ' ')
BACKEND_ERRORS=$(grep -o "error" test_results/backend_output.txt | wc -l | tr -d ' ')

echo -e "  Passed: ${GREEN}${BACKEND_PASSED}${NC}"
echo -e "  Failed: ${RED}${BACKEND_FAILED}${NC}"
echo -e "  Errors: ${RED}${BACKEND_ERRORS}${NC}"
echo ""

# Frontend Build Test
echo -e "${YELLOW}Testing Frontend Build...${NC}"
cd frontend
npm run build > ../test_results/frontend_build.txt 2>&1
FRONTEND_BUILD_EXIT=$?
cd ..

if [ $FRONTEND_BUILD_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Frontend build successful${NC}"
else
    echo -e "${RED}✗ Frontend build failed${NC}"
fi
echo ""

# Generate Summary Report
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Backend Tests:"
echo "  Total Passed: $BACKEND_PASSED"
echo "  Total Failed: $BACKEND_FAILED"
echo "  Total Errors: $BACKEND_ERRORS"
echo ""

echo "Frontend:"
if [ $FRONTEND_BUILD_EXIT -eq 0 ]; then
    echo "  Build Status: ✓ SUCCESS"
else
    echo "  Build Status: ✗ FAILED"
fi
echo ""

# Overall Status
if [ $BACKEND_EXIT -eq 0 ] && [ $FRONTEND_BUILD_EXIT -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Overall Status: ALL TESTS PASSED${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}  Overall Status: SOME TESTS FAILED${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo ""
    echo "Check test_results/ directory for detailed logs"
    exit 1
fi
