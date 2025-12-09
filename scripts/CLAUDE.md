# CLAUDE.md - Scripts Directory

This file provides guidance for working with the utility scripts in CCPRAgents.

## Overview

The `scripts/` directory contains development utility scripts for git hooks setup and automation. These scripts help maintain code quality by running validation checks before git operations.

## Directory Structure

```
scripts/
├── CLAUDE.md                  # This file
├── setup-git-hooks.sh         # Git hooks installation script
└── git-hooks/                 # Git hook scripts
    ├── README.md             # Git hooks documentation
    └── pre-push              # Pre-push validation hook
```

## Available Scripts

### setup-git-hooks.sh

Installs git hooks from `scripts/git-hooks/` to `.git/hooks/`.

**Usage:**
```bash
./scripts/setup-git-hooks.sh
```

**What it does:**
1. Validates running in a git repository
2. Creates `.git/hooks/` directory if needed
3. Copies hook scripts from `scripts/git-hooks/`
4. Makes hooks executable

**Output:**
- Shows each hook being installed
- Reports success/failure count
- Provides usage notes for bypassing hooks

### git-hooks/pre-push

Pre-push hook that runs validation checks before allowing a push.

**Validation Steps:**
1. **Type checking** - Runs `./start-type-check.sh`
2. **Linting** - Runs `./start-lint.sh --all`

**Behavior:**
- Blocks push if type checking fails
- Blocks push if linting fails
- Shows helpful error messages with fix commands
- Proceeds with push only when all checks pass

**Bypass (not recommended):**
```bash
git push --no-verify
```

## Installation

### First-Time Setup

```bash
# Make script executable (if needed)
chmod +x scripts/setup-git-hooks.sh

# Run installation
./scripts/setup-git-hooks.sh
```

### Verification

After installation, verify hooks are in place:
```bash
ls -la .git/hooks/pre-push
```

## Git Hook Details

### Pre-Push Hook Workflow

```
git push
    │
    ▼
┌─────────────────────────┐
│ Step 1: Type Checking   │
│ ./start-type-check.sh   │
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
  Pass           Fail
    │               │
    ▼               ▼
┌───────────┐   Block Push
│ Step 2:   │   Show Error
│ Linting   │
│ ./start-  │
│ lint.sh   │
│ --all     │
└─────┬─────┘
      │
  ┌───┴───┐
  │       │
  ▼       ▼
Pass    Fail
  │       │
  ▼       ▼
Push   Block Push
       Show Error
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks passed, push allowed |
| 1 | Validation failed, push blocked |

## Development Guidelines

### Adding New Hooks

1. Create hook script in `scripts/git-hooks/`
2. Use naming convention matching git hook names
3. Make script executable: `chmod +x scripts/git-hooks/<hook-name>`
4. Re-run setup script to install

### Hook Script Template

```bash
#!/bin/bash

# CCPRAgents - [Hook Name] Git Hook
# [Description of what this hook does]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}[Hook Name]: Running...${NC}"

# Get repository root
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT" || exit 1

# Your validation logic here
if ! your_check_command; then
    echo -e "${RED}Check failed!${NC}"
    exit 1
fi

echo -e "${GREEN}All checks passed!${NC}"
exit 0
```

### Modifying Existing Hooks

1. Edit hook in `scripts/git-hooks/`
2. Re-run `./scripts/setup-git-hooks.sh` to update

## Integration with Development Workflow

### Recommended Workflow

1. **Before Development:**
   ```bash
   ./scripts/setup-git-hooks.sh
   ```

2. **During Development:**
   - Write code
   - Run tests: `./start-unittest.sh --run`
   - Type check: `./start-type-check.sh`
   - Lint: `./start-lint.sh --all`

3. **Before Push:**
   - Pre-push hook automatically validates
   - Fix any issues before pushing

### Related Scripts (Project Root)

| Script | Purpose |
|--------|---------|
| `start-lint.sh` | Code linting with Ruff |
| `start-type-check.sh` | Type checking with ty |
| `start-unittest.sh` | Unit test runner |

## Troubleshooting

### Hook Not Running

```bash
# Check if hook exists and is executable
ls -la .git/hooks/pre-push

# Re-install hooks
./scripts/setup-git-hooks.sh
```

### Permission Denied

```bash
# Make scripts executable
chmod +x scripts/setup-git-hooks.sh
chmod +x scripts/git-hooks/*
```

### Hooks Failing Unexpectedly

```bash
# Run validation scripts directly to see full output
./start-type-check.sh
./start-lint.sh --all
```

### Temporary Bypass

Only use when absolutely necessary:
```bash
git push --no-verify
```

## Notes

- Hooks are local to your clone and not tracked by git
- Each developer must run setup script after cloning
- Hooks require project scripts (`start-*.sh`) to be present
- Pre-push validation ensures code quality before sharing
