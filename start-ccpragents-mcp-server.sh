#!/bin/bash

# CCPRAgents MCP Server Startup Script
# This script starts the CCPRAgents MCP server with link-mode=copy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 CCPRAgents MCP Server${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ uv is not installed${NC}"
    echo -e "${YELLOW}Please install uv: https://docs.astral.sh/uv/getting-started/installation/${NC}"
    exit 1
fi

echo -e "${GREEN}✅ uv is available${NC}"
echo -e "${CYAN}Version: $(uv --version)${NC}"
echo ""

# Check if we're in the correct directory
if [ ! -f "ccpragents/server.py" ]; then
    echo -e "${RED}❌ ccpragents/server.py not found${NC}"
    echo -e "${YELLOW}Please run this script from the CCPRAgents project root directory${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found ccpragents/server.py${NC}"
echo ""

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo -e "${YELLOW}⚠️  pyproject.toml not found${NC}"
    echo -e "${YELLOW}Make sure dependencies are properly configured${NC}"
fi

# Display startup information
echo -e "${BLUE}Starting CCPRAgents MCP Server...${NC}"
echo -e "${CYAN}Command: uv run python ccpragents/server.py --link-mode=copy${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C or Enter to stop the server${NC}"
echo ""

# Start the server
uv run python ccpragents/server.py --link-mode=copy