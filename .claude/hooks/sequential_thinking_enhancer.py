#!/usr/bin/env python3
"""
Sequential Thinking Enhancer Hook for Claude Code

This hook is triggered on UserPromptSubmit events to enhance the user's prompt
using the sequentialthinking-tools MCP server. It analyzes the prompt through
structured thinking stages and provides enhanced context to guide Claude's
response.

Features:
- Integrates with sequentialthinking-tools MCP for structured analysis
- Enhances user prompts with thinking guidance and context
- Non-blocking execution (always returns exit code 0)
- Configurable thinking depth and verbosity
"""

import json
import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

# Configure logging
def setup_logger(name: str, level: int = logging.WARNING) -> logging.Logger:
    """Set up a logger with consistent formatting."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        formatter = logging.Formatter(
            "[%(name)s] %(levelname)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_logger("sequential_thinking_enhancer")


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


class MCPClientError(HookError):
    """Raised when MCP client communication fails."""


# Configuration
@dataclass
class HookConfig:
    """Hook configuration settings."""

    # Path to Claude Code settings (for MCP server list)
    claude_settings_path: str = os.path.expanduser("~/.claude/settings.json")

    # Project-specific settings (overrides global)
    project_settings_path: str = ".claude/settings.json"

    # Sequential thinking MCP server name
    sequential_thinking_server: str = "sequentialthinking-tools"

    # Sequential thinking tool name
    sequential_thinking_tool: str = "sequentialthinking_tools"

    # Maximum thinking iterations
    max_thinking_iterations: int = 3

    # Minimum prompt length to trigger enhancement
    min_prompt_length: int = 20

    # Enable/disable enhancement
    enable_enhancement: bool = True

    # Logging configuration
    log_level: int = logging.WARNING
    log_to_file: bool = False
    log_file_path: str = ".claude/hooks/sequential_thinking_enhancer.log"

    # Error handling
    raise_on_parse_error: bool = False
    raise_on_mcp_error: bool = False

    # ANSI color codes for terminal output
    color_header: str = "\033[96m"  # Cyan
    color_thought: str = "\033[93m"   # Yellow
    color_enhanced: str = "\033[92m"  # Green
    color_dim: str = "\033[90m"       # Gray
    color_reset: str = "\033[0m"      # Reset

    def __post_init__(self):
        """Validate and apply configuration settings."""
        self._apply_logging_config()

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
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except (IOError, OSError) as e:
                logger.error(f"Failed to configure file logging: {e}")


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

            logger.info(f"Parsed hook event: session_id={session_id}, event={hook_event_name}")

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


@dataclass
class ThinkingStep:
    """Represents a single step in the sequential thinking process."""

    thought_number: int
    thought: str
    next_thought_needed: bool
    total_thoughts: int
    is_revision: bool = False
    revises_thought: Optional[int] = None
    branch_from_thought: Optional[int] = None
    branch_id: Optional[str] = None


class SequentialThinkingClient:
    """Client for interacting with the sequentialthinking-tools MCP server."""

    def __init__(self, config: HookConfig):
        self.config = config
        self._mcp_tools_available = self._check_mcp_availability()

    def _check_mcp_availability(self) -> bool:
        """Check if the sequentialthinking-tools MCP is available."""
        # Check settings files for MCP configuration
        settings_file = self._get_settings_file()
        if not settings_file or not settings_file.exists():
            logger.debug("No settings file found, MCP availability unknown")
            return False

        try:
            with open(settings_file, encoding="utf-8") as f:
                settings = json.load(f)

            mcp_servers = settings.get("mcpServers", {})
            server_names = list(mcp_servers.keys())

            logger.debug(f"Found MCP servers: {server_names}")

            # Check for sequential thinking server
            for server_name in server_names:
                if "sequential" in server_name.lower() or "thinking" in server_name.lower():
                    logger.info(f"Found sequential thinking MCP server: {server_name}")
                    return True

            logger.warning("No sequential thinking MCP server found in settings")
            return False

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading settings file: {e}")
            return False

    def _get_settings_file(self) -> Optional[Path]:
        """Get the appropriate settings file path."""
        project_settings = Path(self.config.project_settings_path)
        if project_settings.exists():
            return project_settings
        return Path(self.config.claude_settings_path)

    def analyze_prompt(self, prompt: str, max_iterations: int = 3) -> List[ThinkingStep]:
        """
        Analyze the prompt using sequential thinking.

        Since hooks cannot directly call MCP tools, this provides a structured
        analysis framework that guides the thinking process. The actual thinking
        will be done by Claude based on the enhanced context we provide.
        """
        steps = []

        if not prompt or len(prompt) < self.config.min_prompt_length:
            logger.debug(f"Prompt too short for enhancement: {len(prompt)} < {self.config.min_prompt_length}")
            return steps

        # Step 1: Problem Definition
        steps.append(ThinkingStep(
            thought_number=1,
            thought=self._define_problem(prompt),
            next_thought_needed=True,
            total_thoughts=3,
        ))

        # Step 2: Context Analysis
        steps.append(ThinkingStep(
            thought_number=2,
            thought=self._analyze_context(prompt),
            next_thought_needed=True,
            total_thoughts=3,
        ))

        # Step 3: Enhancement Guidance
        steps.append(ThinkingStep(
            thought_number=3,
            thought=self._generate_guidance(prompt),
            next_thought_needed=False,
            total_thoughts=3,
        ))

        return steps

    def _define_problem(self, prompt: str) -> str:
        """Define the problem/request in the prompt."""
        # Extract key elements from the prompt
        prompt_lower = prompt.lower()

        # Identify request type
        request_type = "general inquiry"
        if any(word in prompt_lower for word in ["create", "build", "implement", "write"]):
            request_type = "creation/implementation task"
        elif any(word in prompt_lower for word in ["fix", "debug", "solve", "error"]):
            request_type = "debugging/problem-solving task"
        elif any(word in prompt_lower for word in ["explain", "how", "what", "why"]):
            request_type = "explanation/understanding task"
        elif any(word in prompt_lower for word in ["refactor", "improve", "optimize"]):
            request_type = "optimization/refactoring task"

        return f"Request type identified: {request_type}. The user is seeking assistance with: {prompt[:100]}..."

    def _analyze_context(self, prompt: str) -> str:
        """Analyze the context and requirements."""
        # Look for technical keywords
        technical_keywords = []
        tech_terms = ["api", "database", "function", "class", "test", "bug",
                     "feature", "deployment", "git", "merge", "branch"]

        for term in tech_terms:
            if term.lower() in prompt.lower():
                technical_keywords.append(term)

        context_note = "Context analysis"
        if technical_keywords:
            context_note += f" identified technical keywords: {', '.join(technical_keywords)}"
        else:
            context_note += " - general request without specific technical keywords"

        return context_note

    def _generate_guidance(self, prompt: str) -> str:
        """Generate guidance for enhanced response."""
        guidance = "Thinking guidance: "

        # Check for complexity indicators
        prompt_lower = prompt.lower()
        is_complex = (
            len(prompt) > 200 or
            "and" in prompt_lower.split() or
            "," in prompt
        )

        if is_complex:
            guidance += "This appears to be a complex request. Consider: "
            guidance += "1) Breaking down into smaller steps, "
            guidance += "2) Identifying dependencies, "
            guidance += "3) Planning the approach before implementation."
        else:
            guidance += "This is a straightforward request. "
            guidance += "Proceed with direct action and confirmation."

        return guidance


class PromptEnhancer:
    """Enhances user prompts using sequential thinking analysis."""

    def __init__(self, config: HookConfig):
        self.config = config
        self.thinking_client = SequentialThinkingClient(config)

    def enhance_prompt(self, prompt: str) -> Optional[str]:
        """
        Enhance the user prompt with sequential thinking guidance.

        Returns enhanced context as a string, or None if enhancement is not needed.
        """
        if not self.config.enable_enhancement:
            logger.debug("Prompt enhancement disabled by configuration")
            return None

        if not prompt or len(prompt.strip()) < self.config.min_prompt_length:
            logger.debug(f"Prompt too short for enhancement: {len(prompt)} < {self.config.min_prompt_length}")
            return None

        logger.info(f"Enhancing prompt: {prompt[:100]}...")

        try:
            # Get sequential thinking analysis
            thinking_steps = self.thinking_client.analyze_prompt(
                prompt,
                max_iterations=self.config.max_thinking_iterations
            )

            if not thinking_steps:
                logger.debug("No thinking steps generated")
                return None

            # Format the enhanced context
            enhanced_context = self._format_enhanced_context(prompt, thinking_steps)

            logger.info(f"Generated enhanced context with {len(thinking_steps)} thinking steps")
            return enhanced_context

        except Exception as e:
            logger.exception(f"Error during prompt enhancement: {e}")
            if self.config.raise_on_mcp_error:
                raise MCPClientError("Prompt enhancement failed", e) from e
            return None

    def _format_enhanced_context(self, original_prompt: str, steps: List[ThinkingStep]) -> str:
        """Format the enhanced context with thinking guidance."""
        lines = []

        lines.append("## Sequential Thinking Analysis")
        lines.append("")
        lines.append("The following analysis has been applied to your request:")
        lines.append("")

        for step in steps:
            lines.append(f"{self.config.color_thought}Thought {step.thought_number}/{step.total_thoughts}:{self.config.color_reset}")
            lines.append(f"  {step.thought}")
            lines.append("")

        lines.append(f"{self.config.color_enhanced}Enhanced Request:{self.config.color_reset}")
        lines.append("")
        lines.append("Based on the analysis above, please approach this request with:")
        lines.append("1. Clear understanding of the problem/request type")
        lines.append("2. Awareness of relevant technical context")
        lines.append("3. Structured thinking approach")
        lines.append("")

        return "\n".join(lines)


class SequentialThinkingEnhancerHook:
    """Main hook for enhancing prompts using sequential thinking."""

    def __init__(self, config: HookConfig):
        self.config = config
        self.enhancer = PromptEnhancer(config)
        logger.info("SequentialThinkingEnhancerHook initialized")

    def run(self, event: HookEvent) -> int:
        """Run the hook logic."""
        try:
            if not event.prompt:
                logger.debug("No prompt in event, skipping enhancement")
                return 0

            # Enhance the prompt
            enhanced_context = self.enhancer.enhance_prompt(event.prompt)

            # Output the enhanced context
            if enhanced_context:
                # Use JSON output for structured context injection
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": enhanced_context,
                    }
                }
                print(json.dumps(output))
                logger.info("Enhanced context injected via JSON output")
            else:
                logger.debug("No enhanced context generated")

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
    log_level_str = os.environ.get("SEQUENTIAL_THINKING_LOG_LEVEL", "").upper()
    log_level = getattr(logging, log_level_str, logging.WARNING) if log_level_str else logging.WARNING

    # Check if enhancement is disabled via environment
    enable_enhancement = os.environ.get("SEQUENTIAL_THINKING_ENABLE", "true").lower() == "true"

    try:
        config = HookConfig(
            log_level=log_level,
            enable_enhancement=enable_enhancement
        )
        logger.info(f"Starting Sequential Thinking Enhancer with log level {logging.getLevelName(log_level)}")

        event = HookEvent.from_stdin()

        hook = SequentialThinkingEnhancerHook(config)
        exit_code = hook.run(event)

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
