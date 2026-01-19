#!/bin/bash

# PRDiffer MCP Server Startup Script
# This script starts the PRDiffer MCP server with link-mode=copy

set -e

# Global variable to track server PID
SERVER_PID=""

# Graceful shutdown function
shutdown_server() {
    echo ""
    echo -e "${YELLOW}🛑 Shutting down PRDiffer MCP Server gracefully...${NC}"

    if [ ! -z "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
        # Send SIGTERM first for graceful shutdown
        kill -TERM "$SERVER_PID" 2>/dev/null

        # Wait up to 10 seconds for graceful shutdown
        local count=0
        while [ $count -lt 10 ] && kill -0 "$SERVER_PID" 2>/dev/null; do
            sleep 1
            count=$((count + 1))
        done

        # If still running, force kill
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            echo -e "${RED}⚠️  Force stopping server...${NC}"
            kill -KILL "$SERVER_PID" 2>/dev/null
        fi
    fi

    echo -e "${GREEN}✅ Server stopped successfully${NC}"
    exit 0
}

# Set up signal handlers
trap shutdown_server SIGINT SIGTERM

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 PRDiffer MCP Server${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if uv is installed, install if not present
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  uv is not installed, installing automatically...${NC}"

    # Detect OS and install uv accordingly
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        echo -e "${CYAN}Installing uv for Linux...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo -e "${CYAN}Installing uv for macOS...${NC}"
        if command -v brew &> /dev/null; then
            brew install uv
        else
            curl -LsSf https://astral.sh/uv/install.sh | sh
            source $HOME/.cargo/env
        fi
    else
        # Windows or other
        echo -e "${RED}❌ Automatic installation not supported for this OS${NC}"
        echo -e "${YELLOW}Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/${NC}"
        exit 1
    fi

    # Verify installation
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}❌ uv installation failed${NC}"
        echo -e "${YELLOW}Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/${NC}"
        exit 1
    fi

    echo -e "${GREEN}✅ uv installed successfully${NC}"
else
    echo -e "${GREEN}✅ uv is available${NC}"
fi

echo -e "${CYAN}uv version: $(uv --version)${NC}"
echo -e "${CYAN}Python version: $(uv run python --version 2>&1)${NC}"
echo ""

# Check if we're in the correct directory
if [ ! -f "prdiffer/server.py" ]; then
    echo -e "${RED}❌ prdiffer/server.py not found${NC}"
    echo -e "${YELLOW}Please run this script from the PRDiffer project root directory${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found prdiffer/server.py${NC}"
echo ""

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo -e "${YELLOW}⚠️  pyproject.toml not found${NC}"
    echo -e "${YELLOW}Make sure dependencies are properly configured${NC}"
fi

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
echo -e "${CYAN}Command: uv sync${NC}"
if uv sync; then
    echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
else
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi
echo ""

# Check if GITHUB_TOKEN environment variable is set
echo -e "${BLUE}Checking GitHub authentication...${NC}"
if [ -z "$GITHUB_TOKEN" ]; then
    echo -e "${RED}❌ GITHUB_TOKEN environment variable is not set${NC}"
    echo ""
    echo -e "${YELLOW}GitHub authentication is required to run PRDiffer MCP Server.${NC}"
    echo ""
    echo -e "${CYAN}To set up authentication, choose one of these options:${NC}"
    echo ""
    echo -e "${PURPLE}Option 1: Set environment variable${NC}"
    echo -e "  export GITHUB_TOKEN=\"your_github_personal_access_token\""
    echo ""
    echo -e "${PURPLE}Option 2: Create a .env file${NC}"
    echo -e "  echo \"GITHUB_TOKEN=your_github_personal_access_token\" > .env"
    echo ""
    echo -e "${CYAN}To generate a GitHub Personal Access Token:${NC}"
    echo -e "  1. Go to: ${BLUE}https://github.com/settings/tokens${NC}"
    echo -e "  2. Click 'Generate new token (classic)'"
    echo -e "  3. Select scopes: repo, read:org, read:user"
    echo -e "  4. Generate and copy the token"
    echo -e "  5. Set it using one of the options above"
    echo ""
    echo -e "${YELLOW}For more information, see the Authentication section in README.md${NC}"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ GITHUB_TOKEN is set${NC}"
fi
echo ""

# Display startup information
echo -e "${BLUE}Starting PRDiffer MCP Server...${NC}"
echo -e "${CYAN}Command: uv run python prdiffer/server.py --transport http${NC}"
echo ""

# Start the server
echo -e "${YELLOW}Press Ctrl+C to stop the server gracefully${NC}"
echo ""

# Start the server in the background and capture its PID
uv run python prdiffer/server.py --transport http &
SERVER_PID=$!

# Wait for the server process to complete
wait $SERVER_PID