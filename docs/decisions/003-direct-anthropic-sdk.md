# ADR-003: Direct Anthropic SDK Over LiteLLM

**Status:** Accepted
**Date:** 2025-12-01

## Context

The platform uses Claude AI for four features:
1. **Claim verification** — Parse property ad claims, verify distances/times against database
2. **Neighborhood narratives** — Generate verification reports with local knowledge
3. **AI chat** — Real-time Q&A about neighborhoods using scored data as context
4. **Report generation** — Comprehensive neighborhood reports with structured JSON output

We needed to decide how to integrate Claude: via the Anthropic SDK/API directly, or via an abstraction layer like LiteLLM.

## Decision

We use the Anthropic API directly via `httpx` (async HTTP client) for claim verification and property intelligence, and the Anthropic Python SDK for streaming endpoints (AI chat, reports).

We explicitly prohibit LiteLLM or similar API key aggregation libraries.

### Why Not LiteLLM?

1. **Supply chain attack surface** — LiteLLM proxies API keys through its routing layer. A compromised LiteLLM dependency means all API keys (Anthropic, OpenAI, etc.) are exposed in a single point of failure. In March 2024, a supply chain attack on a popular AI wrapper library demonstrated this exact risk.

2. **Key aggregation** — LiteLLM's value proposition is "one interface, many models." But we only use one model (Claude). The abstraction adds complexity with zero benefit while centralizing credentials.

3. **Auditability** — Direct API calls are auditable. Every request goes to `https://api.anthropic.com/v1/messages` with headers we control. No hidden routing, no telemetry, no key transformation.

4. **Dependency minimalism** — Direct httpx calls have zero additional dependencies. The Anthropic SDK (used for streaming) is the only AI-related dependency.

### Implementation

```python
# Direct API (claim verification, property intelligence)
async with httpx.AsyncClient(timeout=30.0) as client:
    resp = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={"model": ANTHROPIC_MODEL, "max_tokens": 1500, "messages": [...]},
    )

# SDK (streaming endpoints — AI chat, reports)
client = anthropic.AsyncAnthropic(api_key=api_key)
async with client.messages.stream(...) as stream:
    async for text in stream.text_stream:
        yield f"data: {json.dumps({'text': text})}\n\n"
```

### Security Controls

- `ANTHROPIC_API_KEY` is server-side only — never exposed to frontend
- Frontend accesses AI features through authenticated backend endpoints (`/api/ai-chat`, `/api/verify-claims`, `/api/generate-report`)
- Bandit SAST scans catch credential leaks in CI
- `uv audit` checks for known vulnerabilities in dependencies
- CLAUDE.md enforces: "Never add LiteLLM or similar API key aggregation libraries"

## Consequences

- Single credential path: env var → httpx/SDK → Anthropic API
- No intermediary that could log, route, or expose API keys
- If we ever need multi-model support, we'd add a second direct integration rather than an abstraction layer
- Slightly more boilerplate than LiteLLM for the httpx calls — acceptable trade-off for security
