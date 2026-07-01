from __future__ import annotations
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.graph import render_graph_svg, update_graph_for_candidate
from app.models import Decision, Graph
from app.search import run_search
from app.store import ProjectStore
from app.expand import expand_from_candidate

settings = get_settings()
store = ProjectStore(settings.projects_dir, settings.library_dir, settings.exports_dir)
app = FastAPI(title=settings.app_name)

app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))

def _ctx(pid: Optional[str] = None, scid: Optional[str] = None, mode: str = "map"):
    projects = store.list_projects()
    project = store.get(pid) if pid else (projects[0] if projects else None)

    selected = None
    retrieval = []

    if project:
        retrieval = store.retrieval_items(project)
        if scid:
            try:
                selected = project.get_candidate(scid)
            except KeyError:
                selected = project.candidates[0] if project.candidates else None
        elif project.candidates:
            selected = project.candidates[0]

    graph_svg = render_graph_svg(project.graph if project else Graph(), scid)

    return {
        "request": None,
        "projects": projects,
        "project": project,
        "selected_candidate": selected,
        "retrieval_items": retrieval,
        "graph_svg": graph_svg,
        "mode": mode,
        "export_dir": None,
    }


def _resp(req, ctx):
    ctx["request"] = req
    return templates.TemplateResponse(req, "partials/workspace_bundle.html", ctx)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "page.html", {**_ctx(), "request": request})


@app.get("/projects/{pid}/workspace", response_class=HTMLResponse)
def workspace(request: Request, pid: str, mode: str = "map"):
    return _resp(request, _ctx(pid, mode=mode))


@app.get("/projects/{pid}/retrieval", response_class=HTMLResponse)
def retrieval_view(request: Request, pid: str):
    return _resp(request, _ctx(pid, mode="retrieval"))


@app.post("/projects/{pid}/search", response_class=HTMLResponse)
def search(request: Request, pid: str, query: str = Form(...), limit: int = Form(8)):
    p = store.get(pid)
    res = run_search(query, limit)
    p.replace_candidates(res, query)
    store.save(p)
    focus = p.candidates[0].candidate_id if p.candidates else None
    return _resp(request, _ctx(pid, focus))


@app.post("/projects/{pid}/candidates/{cid}/decision", response_class=HTMLResponse)
def decide(request: Request, pid: str, cid: str, decision: str = Form(...)):
    p = store.get(pid)

    try:
        d = Decision(decision)
    except ValueError:
        raise HTTPException(400, "Invalid decision")

    c = p.set_decision(cid, d)

    if d == Decision.YES:
        update_graph_for_candidate(p, c)
        expansions = expand_from_candidate(c)
        p.add_expansion(expansions)

    store.save(p)
    return _resp(request, _ctx(pid, cid))
