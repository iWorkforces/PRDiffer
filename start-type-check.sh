#!/bin/bash

# CCPRAgents - Type Checking Script
# This script uses mypy to perform static type checking on all Python files

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
MYPY_CONFIG_FILE="pyproject.toml"

echo -e "${BLUE}🔍 CCPRAgents - Type Checking${NC}"
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

# Function to check if mypy is installed
check_mypy() {
    if ! uv run mypy --version &> /dev/null; then
        echo -e "${YELLOW}📦 mypy not found, installing...${NC}"
        echo -e "${CYAN}Installing mypy via uv...${NC}"
        uv pip install mypy

        # Verify installation
        if ! uv run mypy --version &> /dev/null; then
            echo -e "${RED}❌ Failed to install mypy${NC}"
            echo -e "${YELLOW}Please install mypy manually: uv pip install mypy${NC}"
            exit 1
        fi
    fi

    echo -e "${GREEN}✅ mypy is available${NC}"
    echo -e "${CYAN}Version: $(uv run mypy --version)${NC}"
}

# Function to upgrade mypy to latest version
upgrade_mypy() {
    echo -e "${BLUE}🔄 Upgrading mypy to latest version...${NC}"
    echo -e "${CYAN}Upgrading mypy via uv...${NC}"
    uv pip install --upgrade mypy

    echo -e "${GREEN}✅ mypy upgraded to latest version${NC}"
    echo -e "${CYAN}Version: $(uv run mypy --version)${NC}"
    echo ""
}

# Function to show mypy configuration
show_config() {
    echo -e "${BLUE}⚙️  MyPy Configuration:${NC}"

    if [ -f "$MYPY_CONFIG_FILE" ]; then
        echo -e "${GREEN}✅ Using configuration from $MYPY_CONFIG_FILE${NC}"

        # Show relevant mypy configuration if it exists
        if grep -q "\[tool.mypy\]" "$MYPY_CONFIG_FILE" 2>/dev/null; then
            echo -e "${CYAN}Configuration preview:${NC}"
            sed -n '/\[tool\.mypy\]/,/^\[/p' "$MYPY_CONFIG_FILE" | head -20
        fi
    else
        echo -e "${YELLOW}⚠️  No mypy configuration found, using defaults${NC}"
    fi
    echo ""
}

# Function to run mypy type check
run_type_check() {
    echo -e "${BLUE}🔍 Running mypy type check...${NC}"
    echo ""

    # Run mypy with detailed output
    if uv run mypy .; then
        echo ""
        echo -e "${GREEN}✅ No type errors found!${NC}"
        return 0
    else
        echo ""
        echo -e "${YELLOW}⚠️  Type errors detected${NC}"
        return 1
    fi
}

# Function to show type check statistics
show_stats() {
    echo -e "${BLUE}📊 Type Check Statistics:${NC}"
    echo ""

    # Get statistics by error type
    echo -e "${CYAN}Errors by type:${NC}"
    uv run mypy . 2>&1 | grep "error:" | cut -d: -f3 | sed 's/^ *//' | cut -d' ' -f1 | sort | uniq -c | sort -nr || true
    echo ""

    # Get statistics by file
    echo -e "${CYAN}Files with errors:${NC}"
    uv run mypy . 2>&1 | grep "error:" | cut -d: -f1 | sort | uniq -c | sort -nr | head -10 || true
    echo ""
}

# Function to run type check with coverage report
run_coverage() {
    echo -e "${BLUE}📊 Running type check with coverage report...${NC}"
    echo ""

    # Run mypy with coverage report
    uv run mypy . --html-report mypy-report || true

    echo ""
    if [ -d "mypy-report" ]; then
        echo -e "${GREEN}✅ Coverage report generated in mypy-report/${NC}"
        echo -e "${CYAN}Open mypy-report/index.html in your browser to view the report${NC}"
    fi
}

# Function to show detailed help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --check       Run type checking (default)"
    echo "  --stats       Show detailed type error statistics"
    echo "  --coverage    Generate HTML coverage report"
    echo "  --config      Show mypy configuration"
    echo "  --install     Install/upgrade mypy"
    echo "  --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run type check"
    echo "  $0 --stats           # Show statistics"
    echo "  $0 --coverage        # Generate coverage report"
    echo ""
    echo "Environment Variables:"
    echo "  MYPY_CACHE_DIR   Directory for mypy cache"
    echo ""
}

# Function to install/upgrade mypy
install_mypy() {
    echo -e "${BLUE}📦 Installing/upgrading mypy...${NC}"
    echo -e "${CYAN}Installing mypy via uv...${NC}"
    uv pip install --upgrade mypy

    echo -e "${GREEN}✅ mypy installation completed${NC}"
    echo -e "${CYAN}Version: $(uv run mypy --version)${NC}"
}

# Main execution
main() {
    # Parse command line arguments
    ACTION="check"
    SHOW_STATS=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --check)
                ACTION="check"
                shift
                ;;
            --stats)
                SHOW_STATS=true
                shift
                ;;
            --coverage)
                ACTION="coverage"
                shift
                ;;
            --config)
                check_uv
                check_mypy
                show_config
                exit 0
                ;;
            --install)
                check_uv
                install_mypy
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
    check_mypy
    upgrade_mypy
    show_config

    case $ACTION in
        "check")
            if run_type_check; then
                if [ "$SHOW_STATS" = true ]; then
                    show_stats
                fi
                echo -e "${GREEN}🎉 Type checking completed successfully${NC}"
            else
                if [ "$SHOW_STATS" = true ]; then
                    show_stats
                fi
                echo ""
                echo -e "${YELLOW}💡 Review the errors above and fix type issues${NC}"
                exit 1
            fi
            ;;
        "coverage")
            run_coverage
            if [ "$SHOW_STATS" = true ]; then
                show_stats
            fi
            echo -e "${GREEN}🎉 Coverage report generation completed${NC}"
            ;;
    esac
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Type checking interrupted${NC}"; exit 1' INT

# Run main function
main "$@"
