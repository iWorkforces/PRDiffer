<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

## Always open `@/openspec/AGENTS.md` when the request

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

## Use `@/openspec/AGENTS.md` to learn

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

## Leverages MCP (Model Context Protocol) servers for enhanced capabilities

1. **Sequential Thinking Tools MCP** (`mcp__sequentialthinking-tools__sequentialthinking_tools`)
   - Used for structured analysis and validation
   - Provides step-by-step reasoning for impact scoring and recommendations

2. **Tavily MCP** (`mcp__tavily-mcp__tavily-search`, `mcp__tavily-mcp__tavily-extract`)
   - Used for researching industry best practices and standards
   - Provides real-time validation against OWASP, NIST, WCAG, and other standards
   - Enables anti-pattern detection and production readiness checks

3. **Context7 MCP** (`mcp__context7__resolve-library-id`, `mcp__context7__get-library-docs`)
   - Used for technology-specific guidance
   - Provides framework and library best practices
   - Enables stack-aware question generation

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->