from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.expand import expand_from_candidate
from app.graph import render_graph_svg, update_graph_for_candidate
from app.models import Candidate, Decision
from app.search import run_search
from app.store import ProjectStore

settings = get_settings()
store = ProjectStore(settings.projects_dir, settings.library_dir, settings.exports_dir)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

FIXED_SEARCH_LIMIT = 8


def _resolve_selected_candidate(project, selected_candidate_id=""):
    if not project or not project.candidates:
        return None

    if selected_candidate_id:
        try:
            return project.get_candidate(selected_candidate_id)
        except KeyError:
            pass

    return project.candidates[0] if project.candidates else None


def _workspace_context(project=None, *, query="", selected_candidate_id="", active_tab="search", status_message="", status_level="info"):
    selected = _resolve_selected_candidate(project, selected_candidate_id)

    graph_svg = ""
    if project:
        graph_svg = render_graph_svg(
            project.graph,
            selected.candidate_id if selected else None,
            project.project_id,
        )

    return {
        "app_name": settings.app_name,
        "projects": store.list_projects(),
        "project": project,
        "visible_candidates": project.visible_candidates(FIXED_SEARCH_LIMIT) if project else [],
        "search_query": query,
        "selected_candidate": selected,
        "selected_candidate_id": selected.candidate_id if selected else "",
        "graph_svg": graph_svg,
        "accepted_count": sum(1 for c in project.candidates if c.decision == Decision.YES) if project else 0,
        "deferred_count": sum(1 for c in project.candidates if c.decision == Decision.DEFER) if project else 0,
        "rejected_count": sum(1 for c in project.candidates if c.decision == Decision.NO) if project else 0,
        "active_tab": active_tab,
        "status_message": status_message,
        "status_level": status_level,
    }


def _render_workspace(request, project, **kwargs):
    context = _workspace_context(project, **kwargs)
    context["request"] = request
    return templates.TemplateResponse("partials/workspace_bundle.html", context)


# ROUTES

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    projects = store.list_projects()
    project = projects[0] if projects else None
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse("page.html", context)


@app.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, title: str = Form(...)):
    project = store.create_project(title)
    return _render_workspace(request, project, status_message="Project created.", status_level="success")


@app.get("/projects/{pid}/workspace", response_class=HTMLResponse)
def load_workspace(request: Request, pid: str):
    project = store.get(pid)
    return _render_workspace(request, project)


@app.post("/projects/{pid}/search", response_class=HTMLResponse)
def search_project(request: Request, pid: str, query: str = Form(...)):
    project = store.get(pid)
    results = run_search(query, limit=FIXED_SEARCH_LIMIT)

    project.upsert_candidates(results, query=query)
    store.save(project)

    return _render_workspace(
        request,
        project,
        query=query,
        selected_candidate_id=results[0].candidate_id if results else ""
    )


@app.post("/projects/{pid}/candidates/{cid}/decision", response_class=HTMLResponse)
def decide(request: Request, pid: str, cid: str, decision: str = Form(...)):
    project = store.get(pid)

    candidate = project.set_decision(cid, Decision(decision))

    if candidate.decision == Decision.YES:
        update_graph_for_candidate(project, candidate)

    store.save(project)

    return _render_workspace(request, project, selected_candidate_id=cid)


# ✅ CRITICAL: map expansion restored
@app.post("/projects/{pid}/scan_map", response_class=HTMLResponse)
def scan_map(request: Request, pid: str):
    project = store.get(pid)

    accepted = [c for c in project.candidates if c.decision == Decision.YES]

    for candidate in accepted[:3]:
        new_items = expand_from_candidate(candidate)
        project.expansion_candidates.extend(new_items)

    store.save(project)

    return _render_workspace(request, project, active_tab="queue")

