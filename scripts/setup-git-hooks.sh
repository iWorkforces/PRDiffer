#!/bin/bash

# PRDiffer - Git Hooks Setup Script
# This script installs git hooks from scripts/git-hooks/ to .git/hooks/

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 PRDiffer - Git Hooks Setup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Get the root directory of the git repository
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)

if [ -z "$REPO_ROOT" ]; then
    echo -e "${RED}❌ Not a git repository${NC}"
    exit 1
fi

# Change to the repository root
cd "$REPO_ROOT" || exit 1

# Check if the git-hooks directory exists
if [ ! -d "scripts/git-hooks" ]; then
    echo -e "${RED}❌ scripts/git-hooks directory not found${NC}"
    exit 1
fi

# Create .git/hooks directory if it doesn't exist
mkdir -p .git/hooks

# Install hooks
HOOKS_INSTALLED=0
HOOKS_FAILED=0

echo -e "${BLUE}Installing git hooks...${NC}"
echo ""

for hook in scripts/git-hooks/*; do
    if [ -f "$hook" ]; then
        hook_name=$(basename "$hook")

        # Skip non-hook files (like README, etc.)
        if [[ "$hook_name" == *.sh ]] || [[ "$hook_name" == *.md ]] || [[ "$hook_name" == *.txt ]]; then
            continue
        fi

        echo -e "${CYAN}Installing ${hook_name}...${NC}"

        # Copy the hook
        if cp "$hook" ".git/hooks/$hook_name"; then
            # Make it executable
            chmod +x ".git/hooks/$hook_name"
            echo -e "${GREEN}✅ Installed: ${hook_name}${NC}"
            ((HOOKS_INSTALLED++))
        else
            echo -e "${RED}❌ Failed to install: ${hook_name}${NC}"
            ((HOOKS_FAILED++))
        fi
        echo ""
    fi
done

# Summary
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}✅ Hooks installed: ${HOOKS_INSTALLED}${NC}"

if [ $HOOKS_FAILED -gt 0 ]; then
    echo -e "${RED}❌ Hooks failed: ${HOOKS_FAILED}${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Git hooks setup completed successfully!${NC}"
echo ""
echo -e "${YELLOW}Note: The pre-push hook will run type checking and linting before each push.${NC}"
echo -e "${YELLOW}To bypass temporarily (not recommended): git push --no-verify${NC}"
