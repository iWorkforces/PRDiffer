#!/usr/bin/env python3
"""
Agent Skill/MCP Tool Notification Hook for Claude Code

This hook is triggered on UserPromptSubmit events to notify the user about
available MCP tools and Skills that may be relevant to their request.

Features:
- Hybrid detection: Keyword matching + ToolSearch API
- Non-blocking notification (always returns exit code 0)
- Supports both MCP tools and Skills
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


# Configure logging
def setup_logger(name: str, level: int = logging.WARNING) -> logging.Logger:
    """Set up a logger with consistent formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_logger("tool_skill_notifier")


class LogLevel(Enum):
    """Log level enumeration."""

    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class HookError(Exception):
    """Base exception for hook-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        if original_error:
            super().__init__(f"{message}: {original_error}")
        else:
            super().__init__(message)


class ConfigError(HookError):
    """Raised when configuration is invalid or missing."""


class InputParseError(HookError):
    """Raised when input parsing fails."""


# Configuration
@dataclass
class HookConfig:
    """Hook configuration settings."""

    # Path to Claude Code settings (for MCP server list)
    claude_settings_path: str = os.path.expanduser("~/.claude/settings.json")

    # Project-specific settings (overrides global)
    project_settings_path: str = ".claude/settings.json"

    # Minimum confidence score for keyword matching (0.0 - 1.0)
    keyword_min_confidence: float = 0.3

    # Maximum number of tools/skills to suggest
    max_suggestions: int = 5

    # Enable/disable notification types
    notify_mcp_tools: bool = True
    notify_skills: bool = True

    # Logging configuration
    log_level: int = logging.WARNING
    log_to_file: bool = False
    log_file_path: str = ".claude/hooks/tool_skill_notifier.log"

    # Error handling
    raise_on_parse_error: bool = False  # If False, return empty event on parse error
    raise_on_config_error: bool = False  # If False, continue on config errors

    # ANSI color codes for terminal output
    color_header: str = "\033[96m"  # Cyan
    color_tool: str = "\033[93m"  # Yellow
    color_skill: str = "\033[92m"  # Green
    color_dim: str = "\033[90m"  # Gray
    color_reset: str = "\033[0m"  # Reset

    def __post_init__(self):
        """Validate and apply configuration settings."""
        self._validate_confidence()
        self._apply_logging_config()

    def _validate_confidence(self) -> None:
        """Validate confidence score is within valid range."""
        if not 0.0 <= self.keyword_min_confidence <= 1.0:
            raise ConfigError(
                f"keyword_min_confidence must be between 0.0 and 1.0, got {self.keyword_min_confidence}"
            )

    def _apply_logging_config(self) -> None:
        """Apply logging configuration based on settings."""
        global logger
        logger.setLevel(self.log_level)

        if self.log_to_file:
            try:
                log_path = Path(self.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)

                file_handler = logging.FileHandler(log_path)
                file_handler.setLevel(self.log_level)
                formatter = logging.Formatter(
                    "[%(asctime)s] [%(name)s] %(levelname)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except (IOError, OSError) as e:
                logger.error(f"Failed to configure file logging: {e}")


@dataclass
class ToolSuggestion:
    """Represents a suggested tool or skill."""

    name: str
    type: str  # "mcp_tool" or "skill"
    description: str
    confidence: float
    server_name: Optional[str] = None


@dataclass
class HookEvent:
    """Represents a UserPromptSubmit hook event."""

    session_id: str
    hook_event_name: str
    prompt: str

    @classmethod
    def from_stdin(cls) -> "HookEvent":
        """Parse hook event from stdin."""
        try:
            raw_data = sys.stdin.read()
            if not raw_data:
                logger.warning("Received empty input on stdin")
                if config.raise_on_parse_error:
                    raise InputParseError("Empty input received")
                return cls(session_id="", hook_event_name="", prompt="")

            logger.debug(f"Received input: {raw_data[:200]}...")

            data = json.loads(raw_data)

            # Validate required fields
            session_id = data.get("session_id", "")
            hook_event_name = data.get("hook_event_name", "")
            prompt = data.get("prompt", "")

            if not session_id:
                logger.warning("Missing session_id in hook event")
            if not hook_event_name:
                logger.warning("Missing hook_event_name in hook event")
            if not prompt:
                logger.debug("Empty prompt in hook event")

            logger.info(
                f"Parsed hook event: session_id={session_id}, event={hook_event_name}"
            )

            return cls(
                session_id=session_id,
                hook_event_name=hook_event_name,
                prompt=prompt,
            )
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in hook event input: {e}"
            logger.error(error_msg)
            if config.raise_on_parse_error:
                raise InputParseError(error_msg, e) from e
            return cls(session_id="", hook_event_name="", prompt="")
        except (KeyError, TypeError) as e:
            error_msg = f"Error parsing hook event structure: {e}"
            logger.error(error_msg)
            if config.raise_on_parse_error:
                raise InputParseError(error_msg, e) from e
            return cls(session_id="", hook_event_name="", prompt="")
        except Exception as e:
            error_msg = f"Unexpected error reading hook event: {e}"
            logger.exception(error_msg)
            if config.raise_on_parse_error:
                raise InputParseError(error_msg, e) from e
            return cls(session_id="", hook_event_name="", prompt="")


class KeywordMatcher:
    """Matches prompts against tools/skills using keyword analysis."""

    # Common keyword patterns for tool/skill categories
    PATTERNS = {
        "git": ["git", "commit", "push", "pull", "branch", "merge", "checkout"],
        "linting": ["lint", "format", "style", "check", "black", "ruff", "eslint"],
        "testing": ["test", "spec", "coverage", "pytest", "jest"],
        "database": ["database", "db", "sql", "query", "migrate"],
        "web": ["fetch", "http", "api", "web", "url", "request"],
        "search": ["search", "find", "grep", "locate"],
        "file": ["file", "read", "write", "edit", "create", "delete"],
        "docs": ["documentation", "docs", "readme", "guide"],
    }

    def match(self, prompt: str, tool_name: str, tool_desc: str) -> float:
        """Calculate confidence score for keyword matching."""
        prompt_lower = prompt.lower()
        combined_text = f"{tool_name} {tool_desc}".lower()

        score = 0.0

        # Exact phrase matching
        for word in prompt_lower.split():
            if word in combined_text:
                score += 0.2

        # Pattern-based matching
        for category, keywords in self.PATTERNS.items():
            if any(kw in prompt_lower for kw in keywords):
                if any(kw in combined_text for kw in keywords):
                    score += 0.3

        return min(score, 1.0)


class ToolSearchClient:
    """Client for using Claude's ToolSearch API."""

    def __init__(self, config: HookConfig):
        self.config = config

    def search_tools(self, query: str) -> List[Dict]:
        """
        Search for tools using ToolSearch.

        This calls Claude's built-in ToolSearch tool to find relevant tools.
        """
        try:
            # The hook can call the ToolSearch tool via a subprocess
            # or by using the MCP ToolSearch API directly
            # For now, we'll use a placeholder implementation
            return []
        except Exception as e:
            print(f"ToolSearch error: {e}", file=sys.stderr)
            return []


class MCPServerInspector:
    """Inspects configured MCP servers for available tools."""

    def __init__(self, config: HookConfig):
        self.config = config

    def get_configured_mcp_tools(self) -> List[Dict]:
        """Get list of configured MCP tools from settings."""
        tools = []

        # Determine settings file path
        project_settings = Path(self.config.project_settings_path)
        settings_file = (
            project_settings
            if project_settings.exists()
            else Path(self.config.claude_settings_path)
        )

        if not settings_file.exists():
            logger.debug(f"No settings file found at {settings_file}")
            return tools

        try:
            logger.debug(f"Reading MCP configuration from {settings_file}")

            with open(settings_file, encoding="utf-8") as f:
                settings = json.load(f)

            # Extract MCP tools from settings
            mcp_servers = settings.get("mcpServers", {})

            if not mcp_servers:
                logger.debug("No MCP servers configured in settings")
                return tools

            logger.info(f"Found {len(mcp_servers)} MCP server(s) in configuration")

            for server_name, server_config in mcp_servers.items():
                server_tools = server_config.get("tools", [])

                if not isinstance(server_tools, list):
                    logger.warning(
                        f"Invalid tools format for server '{server_name}': expected list, got {type(server_tools).__name__}"
                    )
                    continue

                for tool in server_tools:
                    if not isinstance(tool, dict):
                        logger.warning(
                            f"Invalid tool entry in server '{server_name}': {tool}"
                        )
                        continue

                    tool_name = tool.get("name", "")
                    if not tool_name:
                        logger.warning(
                            f"Tool missing 'name' field in server '{server_name}'"
                        )
                        continue

                    tools.append(
                        {
                            "name": tool_name,
                            "description": tool.get("description", ""),
                            "server_name": server_name,
                            "type": "mcp_tool",
                        }
                    )

            logger.info(f"Successfully loaded {len(tools)} MCP tool(s)")

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in settings file {settings_file}: {e}"
            logger.error(error_msg)
            if self.config.raise_on_config_error:
                raise ConfigError(error_msg, e) from e
        except (IOError, OSError) as e:
            error_msg = f"Error reading settings file {settings_file}: {e}"
            logger.error(error_msg)
            if self.config.raise_on_config_error:
                raise ConfigError(error_msg, e) from e
        except Exception as e:
            error_msg = f"Unexpected error loading MCP configuration: {e}"
            logger.exception(error_msg)
            if self.config.raise_on_config_error:
                raise ConfigError(error_msg, e) from e

        return tools


class SkillsInspector:
    """Inspects configured Skills."""

    KNOWN_SKILLS = {
        "commit": {
            "name": "commit",
            "description": "Create git commits with formatted messages",
            "type": "skill",
        },
        "linting": {
            "name": "linting",
            "description": "Run linting and fix code style issues",
            "type": "skill",
        },
        "typecheck": {
            "name": "typecheck",
            "description": "Run static type checking",
            "type": "skill",
        },
        "openspec:proposal": {
            "name": "openspec:proposal",
            "description": "Create OpenSpec proposals",
            "type": "skill",
        },
        "openspec:apply": {
            "name": "openspec:apply",
            "description": "Apply OpenSpec changes",
            "type": "skill",
        },
    }

    def get_available_skills(self) -> List[Dict]:
        """Get list of available Skills."""
        # Check for openspec skills
        skills = list(self.KNOWN_SKILLS.values())

        # Try to read from openspec configuration if available
        openspec_agents = Path("openspec/AGENTS.md")
        if openspec_agents.exists():
            # Add openspec skills
            skills.extend(
                [
                    {
                        "name": "openspec:archive",
                        "description": "Archive OpenSpec proposals",
                        "type": "skill",
                    },
                ]
            )

        return skills


class MCPSkillNotifier:
    """Main hook for notifying about MCP tools and Skills."""

    def __init__(self, config: HookConfig):
        self.config = config
        self.keyword_matcher = KeywordMatcher()
        self.tool_search_client = ToolSearchClient(config)
        self.mcp_inspector = MCPServerInspector(config)
        self.skills_inspector = SkillsInspector()
        logger.info("MCPSkillNotifier initialized")

    def analyze_prompt(self, prompt: str) -> List[ToolSuggestion]:
        """Analyze prompt and suggest relevant tools/skills."""
        suggestions = []

        if not prompt or not prompt.strip():
            logger.debug("Empty prompt provided for analysis")
            return suggestions

        logger.info(f"Analyzing prompt: {prompt[:100]}...")

        try:
            # Get available tools and skills
            mcp_tools = []
            if self.config.notify_mcp_tools:
                mcp_tools = self.mcp_inspector.get_configured_mcp_tools()
                logger.debug(f"Found {len(mcp_tools)} MCP tools available")

            skills = []
            if self.config.notify_skills:
                skills = self.skills_inspector.get_available_skills()
                logger.debug(f"Found {len(skills)} skills available")

            # Keyword matching
            all_items = mcp_tools + skills

            for item in all_items:
                try:
                    item_name = item.get("name", "")
                    item_desc = item.get("description", "")

                    if not item_name:
                        logger.warning(f"Item missing 'name': {item}")
                        continue

                    confidence = self.keyword_matcher.match(
                        prompt, item_name, item_desc
                    )

                    logger.debug(
                        f"Match score for '{item_name}': {confidence:.2%} "
                        f"(threshold: {self.config.keyword_min_confidence:.0%})"
                    )

                    if confidence >= self.config.keyword_min_confidence:
                        suggestions.append(
                            ToolSuggestion(
                                name=item_name,
                                type=item.get("type", "unknown"),
                                description=item_desc,
                                confidence=confidence,
                                server_name=item.get("server_name"),
                            )
                        )
                except Exception as e:
                    logger.warning(f"Error processing item {item}: {e}")
                    continue

            # Sort by confidence and limit
            suggestions.sort(key=lambda s: s.confidence, reverse=True)
            final_suggestions = suggestions[: self.config.max_suggestions]

            logger.info(
                f"Returning {len(final_suggestions)} suggestion(s) "
                f"from {len(suggestions)} total match(es)"
            )

            return final_suggestions

        except Exception as e:
            logger.exception(f"Error during prompt analysis: {e}")
            return suggestions

    def format_notification(self, suggestions: List[ToolSuggestion]) -> str:
        """Format the notification message."""
        if not suggestions:
            return ""

        lines = []
        lines.append(f"{self.config.color_header}{'=' * 60}{self.config.color_reset}")
        lines.append(
            f"{self.config.color_header} Available Tools/Skills for this task:{self.config.color_reset}"
        )
        lines.append(f"{self.config.color_header}{'=' * 60}{self.config.color_reset}")
        lines.append("")

        for s in suggestions:
            icon = "🔧" if s.type == "mcp_tool" else "⚡"
            color = (
                self.config.color_tool
                if s.type == "mcp_tool"
                else self.config.color_skill
            )

            server_info = f" [{s.server_name}]" if s.server_name else ""
            lines.append(
                f"{icon} {color}{s.name}{server_info}{self.config.color_reset}"
            )
            lines.append(
                f"   {self.config.color_dim}{s.description}{self.config.color_reset}"
            )
            lines.append(
                f"   {self.config.color_dim}Confidence: {s.confidence:.0%}{self.config.color_reset}"
            )
            lines.append("")

        lines.append(
            f"{self.config.color_dim}(Execution will continue automatically){self.config.color_reset}"
        )

        return "\n".join(lines)

    def run(self, event: HookEvent) -> int:
        """Run the hook logic."""
        try:
            if not event.prompt:
                logger.debug("No prompt in event, skipping analysis")
                return 0

            suggestions = self.analyze_prompt(event.prompt)

            if suggestions:
                notification = self.format_notification(suggestions)
                print(notification, file=sys.stderr)
            else:
                logger.debug("No relevant tools/skills found for prompt")

            # Always return 0 to allow execution to continue
            return 0

        except Exception as e:
            logger.exception(f"Error running hook: {e}")
            # Return 0 to allow execution to continue despite errors
            return 0


# Module-level config reference for HookEvent.from_stdin()
config: HookConfig = HookConfig()


def main():
    """Main entry point."""
    global config

    # Parse configuration from environment if available
    log_level_str = os.environ.get("TOOL_SKILL_NOTIFIER_LOG_LEVEL", "").upper()
    log_level = (
        getattr(logging, log_level_str, logging.WARNING)
        if log_level_str
        else logging.WARNING
    )

    try:
        config = HookConfig(log_level=log_level)
        logger.info(
            f"Starting Tool/Skill notifier with log level {logging.getLevelName(log_level)}"
        )

        event = HookEvent.from_stdin()

        notifier = MCPSkillNotifier(config)
        exit_code = notifier.run(event)

        logger.debug(f"Hook completed with exit code: {exit_code}")
        sys.exit(exit_code)

    except ConfigError as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(0)  # Non-blocking: allow execution to continue
    except InputParseError as e:
        logger.critical(f"Input parsing error: {e}")
        sys.exit(0)  # Non-blocking: allow execution to continue
    except KeyboardInterrupt:
        logger.info("Hook interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}")
        sys.exit(0)  # Non-blocking: allow execution to continue


if __name__ == "__main__":
    main()
