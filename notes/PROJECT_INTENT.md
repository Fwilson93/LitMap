# Project intent

## Goal
Keep LitMap Slim focused on one coherent local-first loop:
1. search literature metadata;
2. review candidates in a browser workspace;
3. record yes / no / defer decisions;
4. grow a lightweight literature graph from accepted items;
5. track local PDF/supplement availability;
6. export accepted literature into a LitCap-style handoff directory.

## Design principles
- Keep the repo small enough to understand in one sitting.
- Prefer one Python application over split frontend/backend toolchains.
- Keep context-pack tooling lightweight and deterministic.
- Keep runtime state on disk and easy to inspect.
- Optimise for solo development with quick LLM handoff between chats.

## Current stack
- Python 3.11+
- FastAPI
- Jinja2
- HTMX
- Small server-rendered SVG graph
- JSON file persistence under `data/`
