# API Guide — Ollama & Claude Code Integration
**Version:** 1.0 | **Updated:** 2026-03-11

---

## 1. Overview

Claude Code CLI is redirected to the local Ollama instance on LXC 102 via the
`ANTHROPIC_BASE_URL` environment variable, using Ollama's OpenAI-compatible API
endpoint.

```
Claude Code CLI  →  http://10.0.0.102:11434/v1  →  Ollama  →  qwen2.5-coder:32b
```

---

## 2. Environment Variables

| Variable | Value | Purpose |
|---|---|---|
| `ANTHROPIC_BASE_URL` | `http://10.0.0.102:11434/v1` | Redirects Claude Code to local Ollama |
| `ANTHROPIC_API_KEY` | `ollama` | Placeholder token accepted by Ollama's OpenAI adapter |
| `CLAUDE_CODE_TELEMETRY` | `0` | Disables telemetry |
| `CHECKPOINT_DISABLE` | `1` | Disables checkpointing |
| `ALLOW_DANGEROUS_COMMANDS` | `0` | Prevents execution of dangerous shell commands |

---

## 3. Ollama Native API

The Ollama service on LXC 102 exposes these endpoints on port `11434`:

### 3.1 Generate (POST /api/generate)
```bash
curl http://10.0.0.102:11434/api/generate \
  -d '{"model":"qwen2.5-coder:32b","prompt":"Write a Python hello world","stream":false}'
```

Response fields:
- `model` — Model used
- `response` — Generated text
- `done` — Boolean, true when complete
- `total_duration` — Inference time in nanoseconds

### 3.2 List Models (GET /api/tags)
```bash
curl http://10.0.0.102:11434/api/tags
```

Returns JSON with `models` array. Use this to confirm `qwen2.5-coder:32b` is present.

### 3.3 OpenAI-Compatible Chat (POST /v1/chat/completions)
This is the endpoint Claude Code uses via the `ANTHROPIC_BASE_URL` redirect.

```bash
curl http://10.0.0.102:11434/v1/chat/completions \
  -H "Authorization: Bearer ollama" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:32b",
    "messages": [{"role":"user","content":"Hello"}]
  }'
```

### 3.4 Health Check (GET /)
```bash
curl http://10.0.0.102:11434/
# Returns: "Ollama is running"
```

---

## 4. Model Parameters

| Parameter | Value | Notes |
|---|---|---|
| Model | `qwen2.5-coder:32b` | 32B parameter coding model |
| Context window | 32,768 tokens | Default for qwen2.5-coder |
| RAM requirement | ~22 GB | Loaded into system RAM (CPU inference) |
| Temperature | 0.0 | Recommended for deterministic code generation |
| Format | `json` or default | Use `"format":"json"` for structured output |

---

## 5. Smoke Test Endpoints Used

The `smoke_test_agent.py` script tests:

1. `POST /api/generate` — Tests inference reachability.
2. `GET /api/tags` — Verifies `qwen2.5-coder:32b` is loaded.

---

## 6. Performance Notes

- Inference is CPU-bound on the T5500 (dual Xeon).
- Expect 4–12 tokens/second on 32B model with 24 cores.
- First request after service start incurs a model-load delay (~30–60 s).
- The `ExecStartPost` in `ollama-keepalive.service` pre-warms the model on boot.
- Use `/compact` within Claude Code if context window exceeds capacity.
