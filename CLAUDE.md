# Project Context: Air-Gapped AI Development Station

This project is hosted on an air-gapped Proxmox 9.1 cluster.  
Target Model: `qwen2.5-coder:32b` (local via Ollama on LXC 102)

## Environment Constraints

- **Air-Gapped:** No internet access. Do not attempt to fetch external libraries.
- **Hardware:** Dual CPU (T5500). Inference is CPU-bound; use `/compact` if context lags.
- **Execution:** All AI-generated code must be tested inside the rootless Podman sandbox.

## Build & Test Commands

```bash
# Install (air-gapped)
pip install --no-index --find-links=/local/packages -r requirements.txt

# Run tests
pytest tests/ -v --tb=short

# Run sandbox
podman run --rm -v $(pwd):/app:Z local/python-sandbox python /app/main.py
```

## Workflow Rules

- **Plan First:** Provide an implementation plan before modifying files.
- **No Telemetry:** Ensure all CLI tools have telemetry/analytics disabled.
- **Type Hints:** All Python functions must be annotated.
- **Logging:** Use the `logging` module — no bare `print()` for operational output.
- **Exceptions:** Catch specific exceptions only — no bare `except:` clauses.
