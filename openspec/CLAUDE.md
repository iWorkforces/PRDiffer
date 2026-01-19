# CLAUDE.md - OpenSpec Directory

This file provides guidance for working with OpenSpec spec-driven development in PRDiffer.

**Current Version:** 0.4.7

## Overview

OpenSpec is a spec-driven development workflow system. This directory contains the project specifications, change proposals, and archived changes.

## Directory Structure

```
openspec/
├── CLAUDE.md                   # This file
├── AGENTS.md                   # Instructions for AI coding assistants
├── project.md                  # Project conventions and metadata
├── specs/                      # Current truth - what IS built
│   └── [capability]/           # Single focused capability
│       ├── spec.md             # Requirements and scenarios
│       └── design.md           # Technical patterns (optional)
├── changes/                    # Proposals - what SHOULD change
│   ├── [change-name]/         # Active change proposals
│   │   ├── proposal.md        # Why, what, impact
│   │   ├── tasks.md           # Implementation checklist
│   │   ├── design.md          # Technical decisions (optional)
│   │   └── specs/             # Delta changes
│   │       └── [capability]/
│   │           └── spec.md   # ADDED/MODIFIED/REMOVED
│   └── archive/              # Completed changes
│       └── YYYY-MM-DD-[name]/
```

## Key Concepts

### Specs Directory (`specs/`)
Contains the current truth - what has been built and deployed.

**Each capability has:**
- `spec.md` - Requirements with scenarios
- `design.md` - Technical patterns (optional)

### Changes Directory (`changes/`)
Contains active change proposals - what should be built.

**Each change has:**
- `proposal.md` - Why and what is changing
- `tasks.md` - Implementation checklist
- `design.md` - Technical decisions (optional, see criteria in AGENTS.md)
- `specs/` - Delta changes to apply to capabilities

### Archive Directory (`changes/archive/`)
Contains completed changes that have been deployed.

**Naming convention:** `YYYY-MM-DD-[change-name]`

## Workflow Stages

### Stage 1: Creating Changes
Use when adding features, making breaking changes, or changing architecture.

**Skip proposal for:**
- Bug fixes restoring intended behavior
- Typos, formatting, comments
- Non-breaking dependency updates
- Tests for existing behavior

### Stage 2: Implementing Changes
1. Read `proposal.md` to understand what's being built
2. Read `design.md` (if exists) to review technical decisions
3. Read `tasks.md` to get implementation checklist
4. Implement tasks sequentially
5. Update checklist when all work is done

### Stage 3: Archiving Changes
After deployment:
1. Move `changes/[name]/` → `changes/archive/YYYY-MM-DD-[name]/`
2. Update `specs/` if capabilities changed
3. Run `openspec validate --strict`

## CLI Commands

```bash
# List active changes
openspec list

# List specifications
openspec list --specs

# Show change or spec details
openspec show [item]

# Validate changes or specs
openspec validate [item] --strict

# Archive after deployment
openspec archive <change-id> [--yes|-y]
```

## Spec File Format

### Critical: Scenario Formatting

**CORRECT** (use #### headers):
```markdown
#### Scenario: User login success
- **WHEN** valid credentials provided
- **THEN** return JWT token
```

**WRONG** (don't use bullets or bold):
```markdown
- **Scenario: User login**  ❌
**Scenario**: User login     ❌
### Scenario: User login      ❌
```

Every requirement MUST have at least one scenario.

### Delta Operations

- `## ADDED Requirements` - New capabilities
- `## MODIFIED Requirements` - Changed behavior
- `## REMOVED Requirements` - Deprecated features
- `## RENAMED Requirements` - Name changes

**When to use ADDED vs MODIFIED:**
- ADDED: New capability that can stand alone
- MODIFIED: Changes behavior/scope of existing requirement

## Change ID Naming

- Use kebab-case, short and descriptive
- Prefer verb-led prefixes: `add-`, `update-`, `remove-`, `refactor-`
- Examples: `add-two-factor-auth`, `update-rate-limiting`, `refactor-cache`

## Capability Naming

- Use verb-noun: `user-auth`, `payment-capture`
- Single purpose per capability
- 10-minute understandability rule

## Before Creating Specs

**Context Checklist:**
- Read relevant specs in `specs/[capability]/spec.md`
- Check pending changes in `changes/` for conflicts
- Read `openspec/project.md` for conventions
- Run `openspec list` to see active changes

## Design.md Criteria

Create `design.md` if:
- Cross-cutting change (multiple services/modules)
- New external dependency or significant data model changes
- Security, performance, or migration complexity
- Ambiguity that benefits from technical decisions before coding

Otherwise omit it.

## Best Practices

### Simplicity First
- Default to <100 lines of new code
- Single-file implementations until proven insufficient
- Avoid frameworks without clear justification
- Choose boring, proven patterns

### Clear References
- Use `file.ts:42` format for code locations
- Reference specs as `specs/auth/spec.md`
- Link related changes and PRs

## Further Reading

See `AGENTS.md` for complete workflow documentation including:
- Detailed three-stage workflow
- Proposal structure and format
- Validation and troubleshooting
- Multi-capability examples
- Happy path script
