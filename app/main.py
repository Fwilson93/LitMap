from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
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

# ✅ Fix favicon 404
@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


FIXED_SEARCH_LIMIT = 8
SCAN_TARGET_LIMIT = 3


def _resolve_selected_candidate(project, selected_candidate_id: str = ""):
    if not project or not project.candidates:
        return None

    if selected_candidate_id:
        try:
            return project.get_candidate(selected_candidate_id)
        except KeyError:
            pass

    visible = project.visible_candidates(FIXED_SEARCH_LIMIT)
    if visible:
        return visible[0]

    return project.candidates[0]


def _merge_expansion_candidates(project, incoming) -> int:
    accepted_ids = {c.candidate_id for c in project.candidates}
    seen = {c.candidate_id for c in project.expansion_candidates}

    added = 0

    for item in incoming:
        raw_id = item.candidate_id.removeprefix("exp-")

        if item.candidate_id in project.blacklist or raw_id in project.blacklist:
            continue

        if raw_id in accepted_ids or item.candidate_id in accepted_ids:
            continue

        if item.candidate_id in seen:
            continue

        project.expansion_candidates.append(item)
        seen.add(item.candidate_id)
        added += 1

    return added


def _find_expansion_candidate(project, eid: str):
    for item in project.expansion_candidates:
        if item.candidate_id == eid:
            return item
    raise KeyError(eid)


def _ensure_candidate_from_expansion(project, item):
    cid = item.candidate_id.removeprefix("exp-")

    try:
        candidate = project.get_candidate(cid)
        candidate.title = candidate.title or item.title
    except KeyError:
        candidate = Candidate(
            candidate_id=cid,
            title=item.title,
            authors=[],
            journal="",
            year=None,
            doi=None,
            abstract="",
            reasons=[f"queue:{item.source_type}"] if item.source_type else [],
            keywords=[],
            decision=Decision.UNREVIEWED,
        )
        project.candidates.append(candidate)

    return candidate


def _workspace_context(project=None, *, query="", status_message="", status_level="info",
                       selected_candidate_id="", active_tab="search"):

    projects = store.list_projects()

    selected = _resolve_selected_candidate(project, selected_candidate_id)

    graph_svg = ""
    visible_candidates = []
    retrieval_candidates = []

    if project:
        graph_svg = render_graph_svg(
            project.graph,
            selected.candidate_id if selected else None,
            project.project_id,
            "search",
        )

        visible_candidates = project.visible_candidates(FIXED_SEARCH_LIMIT)

        retrieval_candidates = [
            c for c in project.candidates
            if c.decision in {Decision.YES, Decision.DEFER}
            or c.local_pdf_path
            or c.local_si_path
        ]

    return {
        "app_name": settings.app_name,
        "projects": projects,
        "project": project,
        "visible_candidates": visible_candidates,
        "retrieval_candidates": retrieval_candidates,
        "search_query": query,
        "status_message": status_message,
        "status_level": status_level,
        "selected_candidate": selected,
        "selected_candidate_id": selected.candidate_id if selected else "",
        "graph_svg": graph_svg,
        "accepted_count": sum(1 for c in project.candidates if c.decision == Decision.YES) if project else 0,
        "deferred_count": sum(1 for c in project.candidates if c.decision == Decision.DEFER) if project else 0,
        "rejected_count": sum(1 for c in project.candidates if c.decision == Decision.NO) if project else 0,
        "fixed_search_limit": FIXED_SEARCH_LIMIT,
        "active_tab": active_tab,
    }


def _render_workspace(request: Request, project=None, **kwargs):
    context = _workspace_context(project, **kwargs)
    context["request"] = request
    return templates.TemplateResponse("partials/workspace_bundle.html", context)


# ----------------------------
# ROUTES (FULLY RESTORED)
# ----------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    projects = store.list_projects()
    project = projects[0] if projects else None
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse("page.html", context)


@app.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, title: str = Form(...), description: str = Form("")):
    project = store.create_project(title, description)
    return _render_workspace(
        request,
        project,
        status_message="Project created.",
        status_level="success",
    )


@app.get("/projects/{pid}", response_class=HTMLResponse)
def project_page(request: Request, pid: str, selected: str = "", tab: str = "search"):
    project = store.get(pid)
    context = _workspace_context(project, selected_candidate_id=selected, active_tab=tab)
    context["request"] = request
    return templates.TemplateResponse("page.html", context)


@app.get("/projects/{pid}/workspace", response_class=HTMLResponse)
def project_workspace(request: Request, pid: str, selected: str = "", tab: str = "search"):
    project = store.get(pid)
    return _render_workspace(request, project, selected_candidate_id=selected, active_tab=tab)


@app.post("/projects/{pid}/search", response_class=HTMLResponse)
def search_project(request: Request, pid: str, query: str = Form(...)):
    project = store.get(pid)

    try:
        results = run_search(query, limit=FIXED_SEARCH_LIMIT)
        project.upsert_candidates(results, query=query)
        status = "Search complete."
        level = "success"
    except Exception as e:
        status = f"Search failed: {e}"
        level = "error"

    store.save(project)

    return _render_workspace(
        request,
        project,
        query=query,
        status_message=status,
        status_level=level,
    )


@app.post("/projects/{pid}/candidates/{cid}/decision", response_class=HTMLResponse)
def decide_candidate(request: Request, pid: str, cid: str, decision: str = Form(...)):
    project = store.get(pid)

    candidate = project.set_decision(cid, Decision(decision))

    if candidate.decision == Decision.YES:
        update_graph_for_candidate(project, candidate)

    store.save(project)

    return _render_workspace(
        request,
        project,
        selected_candidate_id=cid,
    )

