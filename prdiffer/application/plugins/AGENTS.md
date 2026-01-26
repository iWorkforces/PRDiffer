# AGENTS.md - Application Plugins

MCP tool plugins: get_pr_diff_plugin.

## OVERVIEW
MCPToolPlugin implementations for modular tool development.

## STRUCTURE
```
prdiffer/application/plugins/
├── get_pr_diff_plugin.py  # GetPRDiffPlugin
└── *plugin.py             # Additional plugins
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| **Add plugin** | New *_plugin.py |
| **Register plugin** | `plugin_manager.py` |

## CONVENTIONS

- Implement MCPToolPlugin interface
- Use FastMCP decorators
- Return structured data
- PluginManager auto-discovers

## ANTI-PATTERNS

- **NO component logic** → Components only
- **NO direct API calls** → Use infrastructure
