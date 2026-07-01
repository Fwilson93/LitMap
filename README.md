# LitMap Slim

A slimmer, local-first literature mapping and retrieval tool built with **FastAPI + Jinja2 + HTMX**.

## What it does (updated scope)
- search literature metadata;
- review candidates and record **yes / no / defer** decisions;
- grow a literature graph;
- expand the graph via **citations, authors, and related work**;
- manage an **expansion queue** for controlled ingestion;
- retrieve and manage PDFs and supplementary material;
- track local file availability and retrieval status;
- export accepted literature into a LitCap-style handoff directory.

## Core architecture concepts

### 1. Search candidates
Initial discovery results from external providers.

### 2. Expansion queue
Candidates generated from:
- citations (forward/backward)
- author-related papers
- topic similarity

These are **not automatically added**.
Users must explicitly:
- Accept
- Ignore (can reappear later)
- Blacklist (never reappear)

### 3. Literature graph
Graph grows only from **accepted papers**.

### 4. Retrieval system (separate workflow)
Dedicated workflow for acquiring:
- PDFs
- supplementary information (SI)

States tracked per paper:
- PDF: present / missing
- SI: present / missing / unknown

Acquisition modes:
- automatic retrieval (open access)
- assisted retrieval via browser interaction
- manual ingress via local folder

## Design principles
- single Python app
- local-first and inspectable data
- minimal dependencies
- deterministic behaviour
- explicit user control over graph growth

## Philosophy
This is not just a search tool.

It is a **controlled literature exploration system** where:
- discovery is automated
- incorporation is deliberate
- retrieval is structured

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn app.main:app --reload
```
