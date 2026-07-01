from __future__ import annotations
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.graph import render_graph_svg, update_graph_for_candidate
from app.models import Decision, Graph, ExpansionCandidate
from app.search import run_search
from app.store import ProjectStore

settings = get_settings()
store = ProjectStore(settings.projects_dir, settings.library_dir, settings.exports_dir)
app = FastAPI(title=settings.app_name)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def _page_context(project_id: Optional[str] = None, selected_candidate_id: Optional[str] = None):
    projects = store.list_projects()
    project = store.get(project_id) if project_id else (projects[0] if projects else None)

    selected_candidate = None
    retrieval_items = []

    if project:
        retrieval_items = store.retrieval_items(project)
        if selected_candidate_id:
            try:
                selected_candidate = project.get_candidate(selected_candidate_id)
            except KeyError:
                selected_candidate = project.candidates[0] if project.candidates else None
        elif project.candidates:
            selected_candidate = project.candidates[0]

    graph_svg = render_graph_svg(project.graph if project else Graph(), selected_candidate_id)

    return {
        "request": None,
        "projects": projects,
        "project": project,
        "selected_candidate": selected_candidate,
        "retrieval_items": retrieval_items,
        "graph_svg": graph_svg,
        "export_dir": None,
    }


def _workspace_response(request: Request, context):
    context["request"] = request
    return templates.TemplateResponse(request, "partials/workspace_bundle.html", context)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context = _page_context()
    context["request"] = request
    return templates.TemplateResponse(request, "page.html", context)


@app.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, title: str = Form(...), description: str = Form("")):
    project = store.create_project(title=title, description=description)
    return _workspace_response(request, _page_context(project.project_id))


@app.post("/projects/{project_id}/search", response_class=HTMLResponse)
def search_project(request: Request, project_id: str, query: str = Form(...), limit: int = Form(8)):
    project = store.get(project_id)
    results = run_search(query=query, limit=limit)
    project.replace_candidates(results, query=query)
    store.save(project)
    focus = project.candidates[0].candidate_id if project.candidates else None
    return _workspace_response(request, _page_context(project_id, focus))


@app.post("/projects/{project_id}/candidates/{candidate_id}/decision", response_class=HTMLResponse)
def decide_candidate(request: Request, project_id: str, candidate_id: str, decision: str = Form(...), notes: str = Form("")):
    project = store.get(project_id)

    try:
        parsed = Decision(decision)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid decision.")

    candidate = project.set_decision(candidate_id, parsed, notes=notes)

    if parsed == Decision.YES:
        update_graph_for_candidate(project, candidate)

        # ✅ ADD expansion placeholder safely
        project.add_expansion([
            ExpansionCandidate(
                candidate_id=f"exp-{candidate_id}",
                title=f"Related to: {candidate.title}",
                source=candidate_id
            )
        ])

    store.save(project)
    return _workspace_response(request, _page_context(project_id, candidate_id))
