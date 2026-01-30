# Codebase Improvements Development Plan - Decisions

## Sprint 1 Decisions
- Use manual caching with RLock instead of @lru_cache for settings
- Upgrade to SHA256 for HMAC verification following GitHub best practices

## Task 3.4: Break Down Large Files - Decision

**3.4a: retry_handler.py (SKIP - Already Done)**
- CircuitBreaker already extracted to circuit_breaker.py (479 lines)
- RequestCoalescingService already extracted to request_coalescing.py (319 lines)
- retry_handler.py is now a composition layer that uses these components
- **Decision**: Mark 3.4a as complete, plan estimates were outdated

**3.4b: mcp_server.py (PROCEED)**
- Single FastMCPServer class with 880 lines
- Good candidate for breaking down into focused modules
- **Plan**: Extract to tool_registry.py, webhook_handler.py, health_endpoints.py

**3.4c: input_validator.py (PROCEED)**
- SecurityPatterns class (~105 lines) + InputValidator class (~635 lines)
- Good candidate for breaking down
- **Plan**: Extract SecurityPatterns and suspicious pattern detection to injection_detector.py, extract sanitization methods to sanitizer.py

**Overall Strategy:**
1. Skip 3.4a (components already extracted)
2. Focus on 3.4b and 3.4c (actual refactoring work)
3. Maintain backward compatibility throughout
4. Create comprehensive tests for new modules

