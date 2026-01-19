#!/bin/bash

# PRDiffer - Unit Testing Script
# This script uses pytest to run all unit tests in the codebase

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
TEST_DIR="tests"
PYTEST_CONFIG_FILE="pyproject.toml"
VENV_DIR="venv"
COVERAGE_MIN=80  # Minimum coverage percentage

echo -e "${BLUE}🧪 PRDiffer - Unit Testing${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

# Function to check if uv is installed
check_uv() {
    if ! command -v uv &> /dev/null; then
        echo -e "${YELLOW}📦 uv not found, installing...${NC}"

        # Install uv using the official installer
        if command -v curl &> /dev/null; then
            echo -e "${CYAN}Installing uv via curl...${NC}"
            curl -LsSf https://astral.sh/uv/install.sh | sh
        elif command -v wget &> /dev/null; then
            echo -e "${CYAN}Installing uv via wget...${NC}"
            wget -qO- https://astral.sh/uv/install.sh | sh
        else
            echo -e "${RED}❌ Neither curl nor wget found. Please install uv manually${NC}"
            echo -e "${YELLOW}Visit: https://docs.astral.sh/uv/getting-started/installation/${NC}"
            exit 1
        fi

        # Source the shell profile to make uv available
        if [ -f "$HOME/.bashrc" ]; then
            source "$HOME/.bashrc"
        elif [ -f "$HOME/.zshrc" ]; then
            source "$HOME/.zshrc"
        fi

        # Add uv to PATH for this session if not already available
        if ! command -v uv &> /dev/null && [ -f "$HOME/.cargo/bin/uv" ]; then
            export PATH="$HOME/.cargo/bin:$PATH"
        fi

        # Verify installation
        if ! command -v uv &> /dev/null; then
            echo -e "${RED}❌ Failed to install uv${NC}"
            echo -e "${YELLOW}Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}✅ uv is available${NC}"
    echo -e "${CYAN}Version: $(uv --version)${NC}"
}

# Function to check if pytest is installed
check_pytest() {
    if ! uv run python -c "import pytest" &> /dev/null; then
        echo -e "${YELLOW}📦 pytest not found, installing...${NC}"
        echo -e "${CYAN}Installing pytest and dependencies via uv...${NC}"
        uv pip install pytest pytest-asyncio pytest-cov pytest-xdist

        # Verify installation
        if ! uv run python -c "import pytest" &> /dev/null; then
            echo -e "${RED}❌ Failed to install pytest${NC}"
            echo -e "${YELLOW}Please install pytest manually: uv pip install pytest${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}✅ pytest is available${NC}"
    PYTEST_VERSION=$(uv run python -c "import pytest; print(pytest.__version__)" 2>/dev/null || echo "unknown")
    echo -e "${CYAN}Version: pytest $PYTEST_VERSION${NC}"
}

# Function to upgrade pytest to latest version
upgrade_pytest() {
    echo -e "${BLUE}🔄 Upgrading pytest to latest version...${NC}"
    echo -e "${CYAN}Upgrading pytest via uv...${NC}"
    uv pip install --upgrade pytest pytest-asyncio pytest-cov pytest-xdist

    echo -e "${GREEN}✅ pytest upgraded to latest version${NC}"
    PYTEST_VERSION=$(uv run python -c "import pytest; print(pytest.__version__)" 2>/dev/null || echo "unknown")
    echo -e "${CYAN}Version: pytest $PYTEST_VERSION${NC}"
    echo ""
}

# Function to find test files
find_test_files() {
    echo -e "${BLUE}🔍 Finding test files...${NC}"

    # Find all test files
    TEST_FILES=$(find "$TEST_DIR" -name "test_*.py" -o -name "*_test.py" | sort)

    if [ -z "$TEST_FILES" ]; then
        echo -e "${YELLOW}⚠️  No test files found in $TEST_DIR${NC}"
        echo -e "${YELLOW}💡 Create test files with names like test_*.py or *_test.py${NC}"
        return 1
    fi

    FILE_COUNT=$(echo "$TEST_FILES" | wc -l)
    echo -e "${GREEN}✅ Found $FILE_COUNT test files${NC}"
    echo ""
    return 0
}

# Function to show pytest configuration
show_config() {
    echo -e "${BLUE}⚙️  Pytest Configuration:${NC}"

    if [ -f "$PYTEST_CONFIG_FILE" ]; then
        if grep -q "\[tool.pytest" "$PYTEST_CONFIG_FILE" 2>/dev/null; then
            echo -e "${GREEN}✅ Using configuration from $PYTEST_CONFIG_FILE${NC}"
            echo -e "${CYAN}Configuration preview:${NC}"
            sed -n '/\[tool\.pytest/,/^\[/p' "$PYTEST_CONFIG_FILE" | head -20
        else
            echo -e "${YELLOW}⚠️  No pytest configuration found in $PYTEST_CONFIG_FILE${NC}"
            echo -e "${CYAN}Using pytest defaults${NC}"
        fi
    elif [ -f "pytest.ini" ]; then
        echo -e "${GREEN}✅ Using configuration from pytest.ini${NC}"
    else
        echo -e "${YELLOW}⚠️  No pytest configuration found, using defaults${NC}"
        echo -e "${CYAN}Tip: Add [tool.pytest.ini_options] to pyproject.toml for custom configuration${NC}"
    fi
    echo ""
}

# Function to run all tests
run_tests() {
    echo -e "${BLUE}🧪 Running all tests...${NC}"
    echo ""

    # Run pytest with verbose output
    if uv run pytest "$TEST_DIR" -v; then
        echo ""
        echo -e "${GREEN}✅ All tests passed!${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Some tests failed${NC}"
        return 1
    fi
}

# Function to run tests with coverage
run_tests_coverage() {
    echo -e "${BLUE}📊 Running tests with coverage analysis...${NC}"
    echo ""

    # Run pytest with coverage
    if uv run pytest "$TEST_DIR" -v --cov=prdiffer --cov-report=term-missing --cov-report=html; then
        echo ""
        echo -e "${GREEN}✅ Tests completed with coverage report${NC}"
        echo -e "${CYAN}📁 HTML coverage report: htmlcov/index.html${NC}"

        # Check coverage percentage
        COVERAGE=$(uv run pytest "$TEST_DIR" --cov=prdiffer --cov-report=term | grep "TOTAL" | awk '{print $NF}' | sed 's/%//' || echo "0")
        if [ ! -z "$COVERAGE" ] && [ "$COVERAGE" != "0" ]; then
            if [ $(echo "$COVERAGE >= $COVERAGE_MIN" | bc -l 2>/dev/null || echo 0) -eq 1 ]; then
                echo -e "${GREEN}✅ Coverage ${COVERAGE}% meets minimum requirement of ${COVERAGE_MIN}%${NC}"
            else
                echo -e "${YELLOW}⚠️  Coverage ${COVERAGE}% is below minimum requirement of ${COVERAGE_MIN}%${NC}"
            fi
        fi
        return 0
    else
        echo ""
        echo -e "${RED}❌ Some tests failed${NC}"
        return 1
    fi
}

# Function to run tests in parallel
run_tests_parallel() {
    echo -e "${BLUE}🚀 Running tests in parallel...${NC}"
    echo ""

    # Run pytest with xdist for parallel execution
    NUM_WORKERS=$(python -c "import os; print(os.cpu_count() or 4)")
    echo -e "${CYAN}Using $NUM_WORKERS parallel workers${NC}"
    echo ""

    if uv run pytest "$TEST_DIR" -v -n "$NUM_WORKERS"; then
        echo ""
        echo -e "${GREEN}✅ All parallel tests passed!${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Some tests failed${NC}"
        return 1
    fi
}

# Function to run specific test file
run_test_file() {
    local file=$1
    echo -e "${BLUE}🧪 Running tests in: $file${NC}"
    echo ""

    if uv run pytest "$file" -v; then
        echo ""
        echo -e "${GREEN}✅ Tests in $file passed!${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Tests in $file failed${NC}"
        return 1
    fi
}

# Function to run tests matching pattern
run_tests_pattern() {
    local pattern=$1
    echo -e "${BLUE}🧪 Running tests matching pattern: $pattern${NC}"
    echo ""

    if uv run pytest "$TEST_DIR" -v -k "$pattern"; then
        echo ""
        echo -e "${GREEN}✅ Tests matching '$pattern' passed!${NC}"
        return 0
    else
        echo ""
        echo -e "${RED}❌ Some tests matching '$pattern' failed${NC}"
        return 1
    fi
}

# Function to show test statistics
show_test_stats() {
    echo -e "${BLUE}📊 Test Statistics:${NC}"
    echo ""

    # Collect test information
    echo -e "${CYAN}Test collection:${NC}"
    uv run pytest "$TEST_DIR" --collect-only -q 2>/dev/null || echo "Unable to collect tests"
    echo ""

    # Show test distribution by file
    echo -e "${CYAN}Tests by file:${NC}"
    find "$TEST_DIR" -name "test_*.py" -o -name "*_test.py" | while read -r file; do
        TEST_COUNT=$(uv run pytest "$file" --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' || echo "0")
        echo "  $(basename $file): $TEST_COUNT tests"
    done
    echo ""
}

# Function to run tests in watch mode
run_tests_watch() {
    echo -e "${BLUE}👀 Running tests in watch mode...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop watching${NC}"
    echo ""

    # Install pytest-watch if needed
    if ! uv run python -c "import pytest_watch" &> /dev/null; then
        echo -e "${CYAN}Installing pytest-watch...${NC}"
        uv pip install pytest-watch
    fi

    # Run pytest-watch
    uv run ptw "$TEST_DIR" -- -v
}

# Function to show detailed help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --run         Run all tests (default)"
    echo "  --coverage    Run tests with coverage analysis"
    echo "  --parallel    Run tests in parallel (faster)"
    echo "  --watch       Run tests in watch mode (re-run on changes)"
    echo "  --file FILE   Run specific test file"
    echo "  --pattern PAT Run tests matching pattern (e.g., 'test_validator')"
    echo "  --stats       Show test statistics"
    echo "  --config      Show pytest configuration"
    echo "  --list        List all test files"
    echo "  --install     Install/upgrade pytest and dependencies"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests"
    echo "  $0 --coverage                        # Run with coverage"
    echo "  $0 --parallel                        # Run in parallel"
    echo "  $0 --file tests/test_validator.py   # Run specific file"
    echo "  $0 --pattern validator               # Run tests matching 'validator'"
    echo "  $0 --watch                           # Watch for changes"
    echo "  $0 --stats                           # Show statistics"
    echo ""
    echo "Environment Variables:"
    echo "  PYTEST_ADDOPTS     Additional pytest options"
    echo "  COVERAGE_MIN       Minimum coverage percentage (default: 80)"
    echo ""
    echo "Common pytest options:"
    echo "  -v, --verbose      Verbose output"
    echo "  -s                 Show print statements"
    echo "  -x                 Stop on first failure"
    echo "  --lf               Run last failed tests"
    echo "  --ff               Run failed tests first"
    echo "  -k PATTERN         Run tests matching pattern"
}

# Function to install/upgrade pytest
install_pytest() {
    echo -e "${BLUE}📦 Installing/upgrading pytest and dependencies...${NC}"
    echo -e "${CYAN}Installing via uv...${NC}"
    uv pip install --upgrade pytest pytest-asyncio pytest-cov pytest-xdist pytest-watch

    echo -e "${GREEN}✅ pytest installation completed${NC}"
    PYTEST_VERSION=$(uv run python -c "import pytest; print(pytest.__version__)" 2>/dev/null || echo "unknown")
    echo -e "${CYAN}Version: pytest $PYTEST_VERSION${NC}"
}

# Function to list test files
list_test_files() {
    echo -e "${BLUE}📁 Test files in the project:${NC}"
    echo ""

    if find_test_files; then
        echo -e "${CYAN}Test files:${NC}"
        echo "$TEST_FILES" | while read -r file; do
            if [ -n "$file" ]; then
                # Count tests in file
                TEST_COUNT=$(uv run pytest "$file" --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' || echo "?")
                echo "  $file ($TEST_COUNT tests)"
            fi
        done
        echo ""
        echo -e "${GREEN}Total: $FILE_COUNT test files${NC}"
    fi
}

# Function to create test directories if they don't exist
ensure_test_structure() {
    if [ ! -d "$TEST_DIR" ]; then
        echo -e "${YELLOW}⚠️  Test directory '$TEST_DIR' not found${NC}"
        echo -e "${CYAN}Creating test directory structure...${NC}"
        mkdir -p "$TEST_DIR/unit/domain"
        mkdir -p "$TEST_DIR/unit/infrastructure"
        mkdir -p "$TEST_DIR/unit/application"
        mkdir -p "$TEST_DIR/integration"

        # Create __init__.py files
        touch "$TEST_DIR/__init__.py"
        touch "$TEST_DIR/unit/__init__.py"
        touch "$TEST_DIR/unit/domain/__init__.py"
        touch "$TEST_DIR/unit/infrastructure/__init__.py"
        touch "$TEST_DIR/unit/application/__init__.py"
        touch "$TEST_DIR/integration/__init__.py"

        echo -e "${GREEN}✅ Test directory structure created${NC}"
        echo -e "${CYAN}You can now add test files in:${NC}"
        echo -e "  - $TEST_DIR/unit/domain/      (domain layer tests)"
        echo -e "  - $TEST_DIR/unit/infrastructure/  (infrastructure layer tests)"
        echo -e "  - $TEST_DIR/unit/application/ (application layer tests)"
        echo -e "  - $TEST_DIR/integration/      (integration tests)"
        echo ""
    fi
}

# Main execution
main() {
    # Parse command line arguments
    ACTION="run"
    TEST_FILE=""
    TEST_PATTERN=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --run)
                ACTION="run"
                shift
                ;;
            --coverage)
                ACTION="coverage"
                shift
                ;;
            --parallel)
                ACTION="parallel"
                shift
                ;;
            --watch)
                ACTION="watch"
                shift
                ;;
            --file)
                ACTION="file"
                TEST_FILE="$2"
                shift 2
                ;;
            --pattern)
                ACTION="pattern"
                TEST_PATTERN="$2"
                shift 2
                ;;
            --stats)
                check_uv
                check_pytest
                ensure_test_structure
                show_test_stats
                exit 0
                ;;
            --config)
                check_uv
                check_pytest
                show_config
                exit 0
                ;;
            --list)
                ensure_test_structure
                list_test_files
                exit 0
                ;;
            --install)
                check_uv
                install_pytest
                exit 0
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Execute main workflow
    check_uv
    check_pytest
    upgrade_pytest
    ensure_test_structure

    # Only try to find test files if we're not in list mode
    if ! find_test_files && [ "$ACTION" != "file" ]; then
        echo -e "${YELLOW}💡 No tests to run. Create test files to get started!${NC}"
        exit 0
    fi

    show_config

    case $ACTION in
        "run")
            if run_tests; then
                echo -e "${GREEN}🎉 Test run completed successfully${NC}"
                exit 0
            else
                echo -e "${RED}❌ Test run failed${NC}"
                exit 1
            fi
            ;;
        "coverage")
            if run_tests_coverage; then
                echo -e "${GREEN}🎉 Coverage test completed successfully${NC}"
                exit 0
            else
                echo -e "${RED}❌ Coverage test failed${NC}"
                exit 1
            fi
            ;;
        "parallel")
            if run_tests_parallel; then
                echo -e "${GREEN}🎉 Parallel test run completed successfully${NC}"
                exit 0
            else
                echo -e "${RED}❌ Parallel test run failed${NC}"
                exit 1
            fi
            ;;
        "watch")
            run_tests_watch
            ;;
        "file")
            if [ -z "$TEST_FILE" ]; then
                echo -e "${RED}❌ No test file specified${NC}"
                echo "Usage: $0 --file <test_file>"
                exit 1
            fi
            if [ ! -f "$TEST_FILE" ]; then
                echo -e "${RED}❌ Test file not found: $TEST_FILE${NC}"
                exit 1
            fi
            if run_test_file "$TEST_FILE"; then
                echo -e "${GREEN}🎉 Test file completed successfully${NC}"
                exit 0
            else
                echo -e "${RED}❌ Test file failed${NC}"
                exit 1
            fi
            ;;
        "pattern")
            if [ -z "$TEST_PATTERN" ]; then
                echo -e "${RED}❌ No pattern specified${NC}"
                echo "Usage: $0 --pattern <pattern>"
                exit 1
            fi
            if run_tests_pattern "$TEST_PATTERN"; then
                echo -e "${GREEN}🎉 Pattern test completed successfully${NC}"
                exit 0
            else
                echo -e "${RED}❌ Pattern test failed${NC}"
                exit 1
            fi
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Testing interrupted${NC}"; exit 1' INT

# Run main function
main "$@"