#!/bin/bash

# PRDiffer MCP Server Startup Script
# This script starts the PRDiffer MCP server with configurable options
#
# Usage:
#   ./start-prdiffer-mcp-server.sh [OPTIONS]
#
# Options:
#   --transport MODE    Transport mode: http, sse, stdio, streamable-http (default: http)
#   --port PORT         Port number for HTTP/SSE transports (default: 9102)
#   --verbose           Enable verbose/debug output
#   --help              Show this help message
#
# Environment Variables:
#   TRANSPORT              Transport mode (overrides --transport)
#   PORT                   Port number (overrides --port)
#   GITHUB_TOKEN           GitHub personal access token (one provider token is required)
#   GITLAB_TOKEN           GitLab personal access token (one provider token is required)
#   GITLAB_ALLOWED_HOSTS   Comma-separated GitLab host allowlist (default: gitlab.com)
#                          e.g. gitlab.com,gitlab.example.com
#   MAX_FILES_ALLOWED      Max selected files for full-context PR/MR diffs (default: 50
#                          from settings.toml app.max_files_allowed; positive integer)
#   GITHUB_IGNORE_PATTERNS Comma-separated ignore globs for GitHub PR file filtering
#                          (replaces settings.toml github.ignore_patterns when set)
#   PID_FILE               Custom PID file location (default: .prdiffer-server.pid)
#
# Configuration:
#   Copy .env.example to .env and fill in tokens / allowlist / limits / ignore list.
#   This script sources .env automatically before starting the server.

set -euo pipefail

# Global variables
SERVER_PID=""
VERBOSE=false
TRANSPORT="${TRANSPORT:-http}"
PORT="${PORT:-9102}"
PID_FILE="${PID_FILE:-.prdiffer-server.pid}"

# Colors for output (must be defined before shutdown_server)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging function with verbose support
log_info() {
    echo -e "${BLUE}ℹ️  $*${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $*${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $*${NC}"
}

log_error() {
    echo -e "${RED}❌ $*${NC}"
}

log_debug() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${CYAN}[DEBUG] $*${NC}"
    fi
}

# Cleanup function for graceful shutdown
cleanup() {
    local exit_code=$?

    # Only shutdown server if we started it
    if [[ -n "$SERVER_PID" ]]; then
        echo ""
        log_warning "Shutting down PRDiffer MCP Server gracefully..."

        if kill -0 "$SERVER_PID" 2>/dev/null; then
            # Send SIGTERM first for graceful shutdown
            kill -TERM "$SERVER_PID" 2>/dev/null || true

            # Wait up to 10 seconds for graceful shutdown
            local count=0
            while [[ $count -lt 10 ]] && kill -0 "$SERVER_PID" 2>/dev/null; do
                sleep 1
                count=$((count + 1))
            done

            # If still running, force kill
            if kill -0 "$SERVER_PID" 2>/dev/null; then
                log_error "Force stopping server..."
                kill -KILL "$SERVER_PID" 2>/dev/null || true
            fi
        fi

        log_success "Server stopped successfully"
    fi

    # Clean up PID file
    if [[ -f "$PID_FILE" ]]; then
        rm -f "$PID_FILE"
        log_debug "Removed PID file: $PID_FILE"
    fi

    exit $exit_code
}

# Parse command-line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --transport)
                TRANSPORT="$2"
                shift 2
                ;;
            --port)
                PORT="$2"
                shift 2
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help message
show_help() {
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# //g' | sed 's/^#//g'
}

# Check for existing server instance
check_existing_server() {
    if [[ -f "$PID_FILE" ]]; then
        local existing_pid
        existing_pid=$(cat "$PID_FILE" 2>/dev/null || echo "")

        if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
            log_warning "Server is already running with PID: $existing_pid"
            read -p "Do you want to stop the existing server and start a new one? [y/N] " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                log_info "Stopping existing server..."
                kill -TERM "$existing_pid" 2>/dev/null || true
                sleep 2
                if kill -0 "$existing_pid" 2>/dev/null; then
                    kill -KILL "$existing_pid" 2>/dev/null || true
                fi
                rm -f "$PID_FILE"
            else
                log_info "Exiting. Use 'kill $existing_pid' to stop the existing server."
                exit 0
            fi
        else
            # Stale PID file, remove it
            rm -f "$PID_FILE"
            log_debug "Removed stale PID file"
        fi
    fi
}

# Load .env file if it exists (see .env.example for keys including GITLAB_ALLOWED_HOSTS, MAX_FILES_ALLOWED, GITHUB_IGNORE_PATTERNS)
load_env_file() {
    if [[ -f .env ]]; then
        log_info "Loading environment variables from .env file"
        # Export variables from .env (GITHUB_TOKEN, GITLAB_TOKEN, GITLAB_ALLOWED_HOSTS, MAX_FILES_ALLOWED, GITHUB_IGNORE_PATTERNS, …)
        set -a
        # shellcheck source=/dev/null
        source .env
        set +a
        log_debug "Loaded .env (GITLAB_ALLOWED_HOSTS=${GITLAB_ALLOWED_HOSTS:-<unset>}, MAX_FILES_ALLOWED=${MAX_FILES_ALLOWED:-<unset>}, GITHUB_IGNORE_PATTERNS=${GITHUB_IGNORE_PATTERNS:-<unset, use settings.toml>})"
    elif [[ -f .env.example ]]; then
        log_debug "No .env file found; copy .env.example to .env to configure tokens, hosts, limits, and ignore list"
    fi
}

# Health check for the server
health_check() {
    local max_attempts=30
    local attempt=0
    local http_port="$PORT"

    log_info "Waiting for server to start..."

    while [[ $attempt -lt $max_attempts ]]; do
        if kill -0 "$SERVER_PID" 2>/dev/null; then
            # For HTTP-based transports, check if the server is responding on the port
            if [[ "$TRANSPORT" == "http" || "$TRANSPORT" == "sse" || "$TRANSPORT" == "streamable-http" ]]; then
                # Check if something is listening on the port
                if command -v nc &> /dev/null; then
                    if nc -z localhost "$http_port" 2>/dev/null; then
                        log_success "Server is running on port $http_port"
                        return 0
                    fi
                elif command -v lsof &> /dev/null; then
                    if lsof -i ":$http_port" &>/dev/null; then
                        log_success "Server is running on port $http_port"
                        return 0
                    fi
                else
                    # Fallback: just verify process is running
                    log_success "Server process is running (PID: $SERVER_PID)"
                    return 0
                fi
            else
                # For stdio, just check if process is running
                log_success "Server process is running (PID: $SERVER_PID)"
                return 0
            fi
        else
            log_error "Server process exited unexpectedly"
            return 1
        fi

        attempt=$((attempt + 1))
        sleep 1
    done

    log_warning "Server health check timed out, but process may still be starting"
    return 0
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Parse arguments
parse_arguments "$@"

# Display startup banner
echo -e "${BLUE}🚀 PRDiffer MCP Server${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Enable verbose output
if [[ "$VERBOSE" == true ]]; then
    log_debug "Verbose mode enabled"
    log_debug "Transport: $TRANSPORT"
    log_debug "Port: $PORT"
    log_debug "PID File: $PID_FILE"
fi

# Check for existing server
check_existing_server

# Load .env file
load_env_file

# Check if uv is installed, install if not present
if ! command -v uv &> /dev/null; then
    log_warning "uv is not installed, installing automatically..."

    # Detect OS and install uv accordingly
    case "$OSTYPE" in
        linux-gnu*)
            log_info "Installing uv for Linux..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            # shellcheck source=/dev/null
            source "$HOME/.cargo/env"
            ;;
        darwin*)
            log_info "Installing uv for macOS..."
            if command -v brew &> /dev/null; then
                brew install uv
            else
                curl -LsSf https://astral.sh/uv/install.sh | sh
                # shellcheck source=/dev/null
                source "$HOME/.cargo/env"
            fi
            ;;
        *)
            log_error "Automatic installation not supported for this OS"
            log_info "Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
            exit 1
            ;;
    esac

    # Verify installation
    if ! command -v uv &> /dev/null; then
        log_error "uv installation failed"
        log_info "Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi

    log_success "uv installed successfully"
else
    log_success "uv is available"
fi

log_info "uv version: $(uv --version)"
log_info "Python version: $(uv run python --version 2>&1)"
echo ""

# Check if we're in the correct directory
if [[ ! -f "prdiffer/server.py" ]]; then
    log_error "prdiffer/server.py not found"
    log_info "Please run this script from the PRDiffer project root directory"
    exit 1
fi

log_success "Found prdiffer/server.py"
echo ""

# Check if pyproject.toml exists
if [[ ! -f "pyproject.toml" ]]; then
    log_warning "pyproject.toml not found"
    log_info "Make sure dependencies are properly configured"
fi

# Install dependencies
log_info "Installing dependencies..."
log_debug "Command: uv sync"
if uv sync; then
    log_success "Dependencies installed successfully"
else
    log_error "Failed to install dependencies"
    exit 1
fi
echo ""

# Check if either provider token environment variable is set
log_info "Checking provider authentication..."
if [[ -z "${GITHUB_TOKEN:-}" && -z "${GITLAB_TOKEN:-}" ]]; then
    log_error "Either GITHUB_TOKEN or GITLAB_TOKEN environment variable must be set"
    echo ""
    echo -e "${YELLOW}GitHub or GitLab authentication is required to run PRDiffer MCP Server.${NC}"
    echo ""
    echo -e "${CYAN}Set a token for either provider using one of these options:${NC}"
    echo ""
    echo -e "${PURPLE}Option 1: Set environment variable${NC}"
    echo -e "  export GITHUB_TOKEN=\"your_github_personal_access_token\""
    echo -e "  export GITLAB_TOKEN=\"your_gitlab_personal_access_token\""
    echo ""
    echo -e "${PURPLE}Option 2: Copy .env.example to .env${NC}"
    echo -e "  cp .env.example .env"
    echo -e "  # then edit .env: GITHUB_TOKEN / GITLAB_TOKEN / GITLAB_ALLOWED_HOSTS / MAX_FILES_ALLOWED"
    echo ""
    echo -e "${CYAN}Generate a personal access token in your selected provider account, then set its environment variable.${NC}"
    echo ""
    echo -e "${YELLOW}For more information, see the Authentication section in README.md${NC}"
    echo ""
    exit 1
else
    log_success "A provider authentication token is set"
fi

# Surface GitLab host allowlist when GitLab is configured (env overrides settings.toml)
if [[ -n "${GITLAB_TOKEN:-}" ]]; then
    if [[ -n "${GITLAB_ALLOWED_HOSTS:-}" ]]; then
        log_info "GitLab allowed hosts (GITLAB_ALLOWED_HOSTS): ${GITLAB_ALLOWED_HOSTS}"
    else
        log_info "GitLab allowed hosts: settings.toml gitlab.allowed_hosts (default gitlab.com)"
        log_debug "Set GITLAB_ALLOWED_HOSTS=gitlab.com,your.gitlab.host for custom instances"
    fi
fi

# Surface selected-file admission limit (env overrides settings.toml app.max_files_allowed)
if [[ -n "${MAX_FILES_ALLOWED:-}" ]]; then
    log_info "Max files allowed (MAX_FILES_ALLOWED): ${MAX_FILES_ALLOWED}"
else
    log_info "Max files allowed: settings.toml app.max_files_allowed (default 50)"
    log_debug "Set MAX_FILES_ALLOWED=N to raise/lower the full-diff selected-file admission limit"
fi

# Surface GitHub ignore patterns when overridden via env
if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    if [[ -n "${GITHUB_IGNORE_PATTERNS:-}" ]]; then
        log_info "GitHub ignore patterns (GITHUB_IGNORE_PATTERNS): ${GITHUB_IGNORE_PATTERNS}"
    else
        log_info "GitHub ignore patterns: settings.toml github.ignore_patterns"
        log_debug "Set GITHUB_IGNORE_PATTERNS=*.lock,node_modules/ to replace the default ignore list"
    fi
fi
echo ""

# Build server command
SERVER_CMD="uv run python prdiffer/server.py"

# Add transport and port for non-stdio modes
if [[ "$TRANSPORT" != "stdio" ]]; then
    SERVER_CMD="$SERVER_CMD --transport $TRANSPORT"
    if [[ -n "$PORT" ]]; then
        SERVER_CMD="$SERVER_CMD --port $PORT"
    fi
fi

# Display startup information
log_info "Starting PRDiffer MCP Server..."
log_debug "Command: $SERVER_CMD"
echo ""

# Start the server
log_info "Press Ctrl+C to stop the server gracefully"
echo ""

# Start the server in the background and capture its PID
eval "$SERVER_CMD" &
SERVER_PID=$!

# Save PID to file
echo "$SERVER_PID" > "$PID_FILE"
log_debug "Saved PID ($SERVER_PID) to $PID_FILE"

# Wait briefly to ensure server started
sleep 1

# Perform health check
if ! health_check; then
    cleanup
    exit 1
fi

# Wait for the server process to complete
wait $SERVER_PID
