# VS Code LLM Bridge Design

> **Date:** 2025-12-25
> **Status:** Ready for implementation
> **Author:** Claude + Varun

## Overview

Replace Azure AI Foundry as the primary LLM provider with a VS Code extension bridge that exposes GitHub Copilot's Language Model API. This provides access to large context window models (128K-1M tokens) without per-token costs.

## Motivation

**Problem:** The EDPS method processes large book sections (up to 67K tokens for Wealth of Nations). The GitHub Models REST API has an 8K token limit, making it unsuitable without complex sub-chunking.

**Solution:** The VS Code Language Model API (via Copilot) provides:
- GPT-5/4o: 128K context window
- Claude Sonnet 4.5: 200K context window
- Gemini 3 Pro: 1M+ context window

This eliminates the need for sub-chunking and enables processing entire sections in single requests.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         EDPS CLI (Python)                       │
├─────────────────────────────────────────────────────────────────┤
│  LLMClient                                                      │
│    ├── provider: "vscode" (primary)                             │
│    └── provider: "azure" (fallback)                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          ▼                                 ▼
┌─────────────────────┐          ┌─────────────────────┐
│  VS Code Extension  │          │   Azure AI Foundry  │
│  (edps-llm-bridge)  │          │   (fallback)        │
├─────────────────────┤          └─────────────────────┘
│  HTTP Server        │
│  - POST /complete   │
│  - GET /health      │
│  - GET /models      │
├─────────────────────┤
│  Discovery file:    │
│  ~/.edps/server.json│
├─────────────────────┤
│  Lifecycle:         │
│  - Auto-start       │
│  - 10-min timeout   │
│  - Dynamic port     │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  vscode.lm API      │
│  (Copilot models)   │
└─────────────────────┘
```

## Components

### 1. VS Code Extension: `edps-llm-bridge`

A minimal, dedicated extension that exposes an HTTP server for LLM requests.

**Activation:** Auto-start on first HTTP request
**Shutdown:** After 10 minutes of idle time
**Port:** Dynamic (writes to discovery file)

#### Discovery File

Location: `~/.edps/server.json`

```json
{
  "port": 52341,
  "pid": 12345,
  "started": "2025-12-25T10:30:00Z",
  "models": ["gpt-5", "claude-sonnet-4.5", "gemini-3-pro"]
}
```

#### HTTP Endpoints

**POST /complete**
```json
// Request
{
  "model": "claude-sonnet-4.5",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "max_tokens": 4096,
  "temperature": 0.3
}

// Response
{
  "content": "...",
  "usage": {
    "input_tokens": 1234,
    "output_tokens": 567
  }
}
```

**GET /health**
```json
{
  "status": "ok",
  "uptime": 300
}
```

**GET /models**
```json
{
  "models": [
    {"id": "gpt-5", "context_window": 128000},
    {"id": "claude-sonnet-4.5", "context_window": 200000},
    {"id": "gemini-3-pro", "context_window": 1000000}
  ]
}
```

### 2. Python Client Changes

#### Config Structure

```yaml
# ~/.edps/config.yaml

provider: "vscode"  # Primary: "vscode", fallback: "azure"

vscode:
  discovery_file: "~/.edps/server.json"
  timeout: 30  # Request timeout in seconds

azure:  # Fallback when VS Code unavailable
  endpoint: "https://..."
  api_key: "${AZURE_API_KEY}"

models:
  summary: "gemini-3-pro"
  quiz: "claude-sonnet-4.5"
  claims_synthesis: "gpt-5"

council:
  enabled: true
  tasks: ["evaluation"]
  models:
    - "gpt-5"
    - "claude-sonnet-4.5"
    - "gemini-3-pro"
  chair: "gpt-5"
  stages: 3

defaults:
  temperature: 0.3
  max_tokens: 4096
```

#### LLMClient Updates

```python
class LLMClient:
    def __init__(self, config: EdpsConfig):
        self.provider = config.provider
        self.vscode_config = config.vscode
        self.azure_config = config.azure

    def complete(self, prompt, model=None, ...) -> LLMResponse:
        if self.provider == "vscode":
            try:
                return self._complete_vscode(prompt, model, ...)
            except VSCodeUnavailableError:
                if self._has_azure_fallback():
                    return self._complete_azure(prompt, model, ...)
                raise
        return self._complete_azure(prompt, model, ...)

    def _complete_vscode(self, prompt, model, ...) -> LLMResponse:
        server_info = self._read_discovery_file()
        if not server_info:
            raise VSCodeUnavailableError("Server not running")

        response = requests.post(
            f"http://localhost:{server_info['port']}/complete",
            json={"model": model, "messages": [...], ...},
            timeout=self.vscode_config.timeout
        )
        return LLMResponse(...)
```

### 3. LLM Council (Evaluation Only)

For the evaluation task, use a 3-stage council with diverse models:

```
Stage 1: Independent Answers
  GPT-5 ──────────────▶ Answer A
  Claude Sonnet 4.5 ──▶ Answer B
  Gemini 3 Pro ───────▶ Answer C

Stage 2: Cross-Review
  GPT-5 reviews B+C ──▶ Review A
  Claude reviews A+C ─▶ Review B
  Gemini reviews A+B ─▶ Review C

Stage 3: Chair Synthesis
  GPT-5 (chair) receives all answers + reviews
  ──────────────────────▶ Final Evaluation
```

**Request count:** 7 per evaluation (stages 1 & 2 run in parallel batches)

**Configurable stages:**
- `stages: 3` - Full council (default)
- `stages: 2` - Skip cross-review
- `stages: 1` - Single model (no council)

## Model Selection

| Task | Model | Rationale |
|------|-------|-----------|
| Summary | `gemini-3-pro` | Largest context window (1M+), handles any section |
| Quiz | `claude-sonnet-4.5` | High quality question generation |
| Claims synthesis | `gpt-5` | Strong analytical reasoning |
| Evaluation | Council | Diverse perspectives for fair grading |

## Error Handling

| Scenario | Detection | Response |
|----------|-----------|----------|
| VS Code not running | `server.json` missing/stale | Fall back to Azure |
| Extension not installed | No discovery file ever | Error: "Install extension" |
| Server crashed | PID exists, port dead | Delete stale file, retry |
| Rate limited | HTTP 429 | Exponential backoff (3 attempts) |
| Model unavailable | Extension error | Fall back to different model |
| Request timeout | No response in 30s | Retry once, then fail |

## User Feedback

```
$ edps generate wealth-of-nations 001 --type summary

[VS Code] Connected to LLM bridge (port 52341)
[VS Code] Using model: gemini-3-pro
Generating summary for section 001...
✓ Created summary.md (12,345 tokens in, 1,234 out, 3.2s)
```

```
$ edps generate wealth-of-nations 001 --type summary

[Warning] VS Code LLM bridge not available
[Fallback] Using Azure (claude-sonnet-4)
Generating summary for section 001...
✓ Created summary.md (12,345 tokens in, 1,234 out, 2.8s)
```

## Files to Create/Modify

### New Files

1. **VS Code Extension** (new project)
   - `edps-llm-bridge/`
     - `package.json` - Extension manifest
     - `src/extension.ts` - Activation, server lifecycle
     - `src/server.ts` - HTTP server implementation
     - `src/lmClient.ts` - VS Code LM API wrapper

2. **Python**
   - `tools/edps/core/vscode_client.py` - VS Code bridge client
   - `tools/edps/core/council.py` - LLM council implementation

### Modified Files

1. `tools/edps/config.py` - Add VSCodeConfig, CouncilConfig
2. `tools/edps/core/llm.py` - Add provider routing, fallback logic
3. `tools/edps/evaluation.py` - Integrate council for evaluation task

## Testing Plan

1. **Unit tests**
   - Config parsing with new fields
   - Discovery file read/write
   - Council stage logic

2. **Integration tests**
   - HTTP server endpoints
   - Python client ↔ Extension communication
   - Fallback to Azure

3. **A/B testing**
   - Council (3-stage) vs single model evaluation
   - Compare feedback quality

## Future Considerations

- **Sub-chunking** (deferred): Not needed with large context windows, but could add for edge cases
- **Streaming** (deferred): Extension supports it, could add for real-time feedback
- **Model auto-selection** (deferred): Choose model based on input size

## Decision Log

| Question | Decision | Rationale |
|----------|----------|-----------|
| Primary provider | VS Code LM API | Large context windows (vs 8K REST API) |
| Bridge approach | HTTP server | Simple, reliable, debuggable |
| Extension scope | New dedicated extension | Clean separation from GitHub LLM Council |
| Server lifecycle | Auto-start, 10-min timeout | Minimal interaction, low memory |
| Port | Dynamic with discovery file | Avoids conflicts |
| Council scope | Evaluation only | Other tasks don't benefit from multiple perspectives |
| Council models | GPT-5, Claude, Gemini | Provider diversity |
| Chair model | GPT-5 | Strong synthesis capabilities |
