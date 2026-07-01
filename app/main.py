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

settings = get_settings()
store = ProjectStore(settings.projects_dir, settings.library_dir, settings.exports_dir)

app = FastAPI(title=settings.app_name)

app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).resolve().parent / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


def _page_context(
    project_id: Optional[str] = None,
    selected_candidate_id: Optional[str] = None,
) -> dict[str, object]:

    projects = store.list_projects()
    project = (
        store.get(project_id)
        if project_id
        else (projects[0] if projects else None)
    )

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

    graph_svg = render_graph_svg(
        project.graph if project else Graph(),
        selected_candidate_id=selected_candidate_id,
    )

    return {
        "request": None,
        "app_name": settings.app_name,
        "projects": projects,
        "project": project,
        "selected_candidate": selected_candidate,
        "retrieval_items": retrieval_items,
        "graph_svg": graph_svg,
        "export_dir": None,
    }


def _workspace_response(request: Request, context: dict[str, object]) -> HTMLResponse:
    context["request"] = request
    return templates.TemplateResponse(request, "partials/workspace_bundle.html", context)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    context = _page_context()
    context["request"] = request
    return templates.TemplateResponse(request, "page.html", context)


@app.get("/projects/{project_id}/workspace", response_class=HTMLResponse)
def project_workspace(
    request: Request,
    project_id: str,
    candidate_id: Optional[str] = None,
) -> HTMLResponse:
    return _workspace_response(request, _page_context(project_id, candidate_id))


@app.post("/projects", response_class=HTMLResponse)
def create_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
) -> HTMLResponse:
    project = store.create_project(title=title, description=description)
    return _workspace_response(request, _page_context(project.project_id))


@app.post("/projects/{project_id}/search", response_class=HTMLResponse)
def search_project(
    request: Request,
    project_id: str,
    query: str = Form(...),
    limit: int = Form(8),
) -> HTMLResponse:
    project = store.get(project_id)

    results = run_search(query=query, limit=limit)

    # ✅ NEW behaviour (replace, not accumulate)
    project.replace_candidates(results, query=query)

    store.save(project)

    focus = project.candidates[0].candidate_id if project.candidates else None

    return _workspace_response(request, _page_context(project_id, focus))


@app.post(
    "/projects/{project_id}/candidates/{candidate_id}/select",
    response_class=HTMLResponse,
)
def select_candidate(
    request: Request,
    project_id: str,
    candidate_id: str,
) -> HTMLResponse:
    return _workspace_response(request, _page_context(project_id, candidate_id))


@app.post(
    "/projects/{project_id}/candidates/{candidate_id}/decision",
    response_class=HTMLResponse,
)
def decide_candidate(
    request: Request,
    project_id: str,
    candidate_id: str,
    decision: str = Form(...),
    notes: str = Form(""),
) -> HTMLResponse:

    project = store.get(project_id)

    try:
        parsed = Decision(decision)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid decision.") from exc

    candidate = project.set_decision(candidate_id, parsed, notes=notes)

    if parsed == Decision.YES:
        update_graph_for_candidate(project, candidate)

    store.save(project)

    return _workspace_response(request, _page_context(project_id, candidate_id))


@app.post("/projects/{project_id}/library/scan", response_class=HTMLResponse)
def scan_library(
    request: Request,
    project_id: str,
    candidate_id: Optional[str] = Form(None),
) -> HTMLResponse:

    project = store.get(project_id)
    store.scan_library(project)

    return _workspace_response(request, _page_context(project_id, candidate_id))


@app.post("/projects/{project_id}/export", response_class=HTMLResponse)
def export_project(
    request: Request,
    project_id: str,
    candidate_id: Optional[str] = Form(None),
) -> HTMLResponse:

    project = store.get(project_id)
    export_dir = store.export_project(project)

    context = _page_context(project_id, candidate_id)

    try:
        context["export_dir"] = export_dir.relative_to(settings.repo_root)
    except ValueError:
        context["export_dir"] = export_dir

    return _workspace_response(request, context)
