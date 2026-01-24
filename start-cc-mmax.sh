#!/bin/zsh

# Exit on errors, undefined variables, and pipe failures
set -euo pipefail

# Load environment variables from .env.cc.mmax
SCRIPT_DIR="${0:A:h}"
ENV_FILE="${SCRIPT_DIR}/.env.cc.mmax"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: .env.cc.mmax not found at $ENV_FILE" >&2
    echo "" >&2
    echo "To get started, copy an example file:" >&2
    echo "  cp .env.cc.mmax.example .env.cc.mmax   # or .env.cc.mmax.zai.example" >&2
    echo "Then edit .env.cc.mmax with your API keys." >&2
    exit 1
fi

# Handle script flags (--help, --debug)
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    cat <<'EOF'
OpenCC - Claude Code wrapper for OpenRouter/Z.ai

Usage:
    ./start-cc.sh [claude options]
    ./start-cc.sh --debug [claude options]
    ./start-cc.sh --help

Environment:
    Loads configuration from .env.cc.mmax in the script directory.

Examples:
    ./start-cc.sh
    ./start-cc.sh --dangerously-skip-permissions
    ./start-cc.sh --debug --help
EOF
    exit 0
fi

if [[ "${1:-}" == "--debug" ]]; then
    shift
    set -x  # Enable zsh tracing
fi

is_secret() {
    local key="$1"

    # Variables matching secret patterns but explicitly excluded from masking
    case "$key" in
        API_TIMEOUT_MS|CLAUDE_CODE_MAX_OUTPUT_TOKENS|MAX_MCP_OUTPUT_TOKENS|MAX_THINKING_TOKENS)
            return 1
            ;;
    esac

    local key_lower="${1:l}"
    if [[ $key_lower == *api* || $key_lower == *key* || $key_lower == *secret* || $key_lower == *token* || $key_lower == *pass* || $key_lower == *pwd* ]]; then
        return 0
    fi
    return 1
}

mask_value() {
    local val="$1"
    local len="${#val}"
    if [[ $len -lt 8 ]]; then
        echo "***"
    else
        echo "${val:0:4}***${val:(-4)}"
    fi
}

# Read and export each KEY=VALUE line
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    key="${line%%=*}"
    value="${line#*=}"

    # Validate key name (must start with letter/underscore, contain only alphanumeric/underscore)
    if [[ -z "$key" ]] || [[ "$key" =~ [^A-Za-z0-9_] ]] || [[ "$key" =~ ^[0-9] ]]; then
        echo "Warning: Skipping invalid environment variable name: '$key'" >&2
        continue
    fi

    # Strip outer quotes if present
    if [[ "$value" == \"*\" ]]; then
        value="${value#\"}"
        value="${value%\"}"
    elif [[ "$value" == \'*\' ]]; then
        value="${value#\'}"
        value="${value%\'}"
    fi
    if is_secret "$key"; then
        masked_value=$(mask_value "$value")
        echo "$key=$masked_value"
    else
        echo "$key=$value"
    fi
    export "$key=$value"
done < "$ENV_FILE"

# OpenRouter/Z.ai app attribution headers (if configured)
# Pattern matches with or without subdomain, with or without trailing path
if [[ "$ANTHROPIC_BASE_URL" == *://(*.)openrouter.ai(/*) || "$ANTHROPIC_BASE_URL" == *://(*.)z.ai(/*) ]]; then
    if [[ -n "${OPENROUTER_APP_URL:-}" ]] && [[ -n "${OPENROUTER_APP_NAME:-}" ]]; then
        ANTHROPIC_CUSTOM_HEADERS="HTTP-Referer:${OPENROUTER_APP_URL},X-Title:${OPENROUTER_APP_NAME}"
        masked_url="${OPENROUTER_APP_URL:0:20}..."
        masked_name="${OPENROUTER_APP_NAME:0:20}..."
        echo "ANTHROPIC_CUSTOM_HEADERS=HTTP-Referer:[$masked_url],X-Title:[$masked_name]"
        export ANTHROPIC_CUSTOM_HEADERS
    fi
fi

# Validate required environment variable (checked first since env file is this script's primary purpose)
if [[ -z "$ANTHROPIC_AUTH_TOKEN" ]]; then
    # Distinguish between "not set" and "empty" using ${(t)var} type expansion
    if [[ -z "${(t)ANTHROPIC_AUTH_TOKEN}" ]]; then
        echo "Error: ANTHROPIC_AUTH_TOKEN is not defined in $ENV_FILE" >&2
    else
        echo "Error: ANTHROPIC_AUTH_TOKEN is empty in $ENV_FILE" >&2
    fi
    exit 1
fi

# Check if claude command exists
if ! command -v claude &>/dev/null; then
    echo "Error: 'claude' command not found." >&2
    echo "Install from https://claude.ai/code" >&2
    exit 1
fi

# Execute claude with any passed arguments
exec claude "$@"
