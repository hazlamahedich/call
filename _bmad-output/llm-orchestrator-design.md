# LLM Provider Abstraction Design (LLMOrchestrator)

**Status**: Design Document
**Owner**: Winston (Architect)
**Deadline**: Before Story 3.3
**Pattern**: Follows TTSOrchestrator architecture from Epic 2

---

## Overview

This document designs the LLM provider abstraction for Stories 3.3 (Script Generation) and 3.6 (Self-Correction). The design mirrors the successful TTSOrchestrator pattern from Story 2.3.

## Key Components

1. **Abstract Base Class**: LLMProviderBase with generate(), health_check(), count_tokens()
2. **OpenAI Provider**: GPT-4 / GPT-3.5 implementation
3. **Anthropic Provider**: Claude implementation
4. **LLM Orchestrator**: Provider selection, fallback, health tracking, circuit breaker
5. **Factory Function**: Singleton pattern with reset_for_tests()

## Architecture Highlights

- **Health-based selection**: Providers ranked by health score (latency + success rate)
- **Automatic fallback**: Degraded providers trigger circuit breaker with cooldown
- **Session state**: Multi-turn conversation history (TODO: migrate to Redis for horizontal scaling)
- **Token counting**: Provider-specific token estimation for cost tracking

## Usage Example

```python
from services.llm.factory import get_llm_orchestrator
from services.llm.base import LLMRequest

orchestrator = get_llm_orchestrator()

request = LLMRequest(
    prompt="Generate sales script",
    max_tokens=500,
    temperature=0.8,
    system_prompt="You are expert sales scriptwriter",
)

response = await orchestrator.generate(request)
```

## Implementation Location

- **Base**: `apps/api/services/llm/base.py`
- **OpenAI**: `apps/api/services/llm/openai.py`
- **Anthropic**: `apps/api/services/llm/anthropic.py`
- **Orchestrator**: `apps/api/services/llm/orchestrator.py`
- **Factory**: `apps/api/services/llm/factory.py`

## Configuration Required

Add to `apps/api/config/settings.py`:
- OPENAI_API_KEY
- OPENAI_MODEL (default: "gpt-4")
- ANTHROPIC_API_KEY
- ANTHROPIC_MODEL (default: "claude-3-sonnet-20240229")
- LLM_HEALTH_THRESHOLD (default: 0.7)
- LLM_CIRCUIT_BREAKER_COOLDOWN (default: 60)

## Testing Strategy

- Mock both providers in unit tests
- Test fallback behavior with simulated failures
- Test health score degradation and recovery
- Integration tests with dev API keys

---

**See full implementation guide in the project repository.**
