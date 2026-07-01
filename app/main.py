from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.expand import expand_from_candidate
from app.graph import render_graph_svg, update_graph_for_candidate
from app.models import Decision
from app.search import run_search
from app.store import ProjectStore

settings = get_settings()
store = ProjectStore(settings.projects_dir, settings.library_dir, settings.exports_dir)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
    accepted_ids = {candidate.candidate_id for candidate in project.candidates}
    seen = {candidate.candidate_id for candidate in project.expansion_candidates}
    added = 0
    for item in incoming:
        raw_candidate_id = item.candidate_id.removeprefix("exp-")
        if item.candidate_id in project.blacklist or raw_candidate_id in project.blacklist:
            continue
        if raw_candidate_id in accepted_ids or item.candidate_id in accepted_ids:
            continue
        if item.candidate_id in seen:
            continue
        project.expansion_candidates.append(item)
        seen.add(item.candidate_id)
        added += 1
    return added


def _render_workspace(request: Request, project=None, **kwargs):
    context = _workspace_context(project, **kwargs)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


def _workspace_context(
    project=None,
    *,
    query: str = "",
    status_message: str = "",
    selected_candidate_id: str = "",
    active_tab: str = "search",
):
    projects = store.list_projects()
    selected_candidate = _resolve_selected_candidate(project, selected_candidate_id)
    graph_svg = ""
    visible_candidates = []
    retrieval_candidates = []
    if project:
        graph_svg = render_graph_svg(
            project.graph,
            selected_candidate.candidate_id if selected_candidate else None,
            project.project_id,
        )
        visible_candidates = project.visible_candidates(FIXED_SEARCH_LIMIT)
        retrieval_candidates = [
            candidate
            for candidate in project.candidates
            if candidate.decision in {Decision.YES, Decision.DEFER} or candidate.local_pdf_path or candidate.local_si_path
        ]
    accepted_count = sum(1 for candidate in project.candidates if candidate.decision == Decision.YES) if project else 0
    deferred_count = sum(1 for candidate in project.candidates if candidate.decision == Decision.DEFER) if project else 0
    rejected_count = sum(1 for candidate in project.candidates if candidate.decision == Decision.NO) if project else 0
    return {
        "app_name": settings.app_name,
        "projects": projects,
        "project": project,
        "visible_candidates": visible_candidates,
        "retrieval_candidates": retrieval_candidates,
        "search_query": query,
        "status_message": status_message,
        "selected_candidate": selected_candidate,
        "selected_candidate_id": selected_candidate.candidate_id if selected_candidate else "",
        "graph_svg": graph_svg,
        "accepted_count": accepted_count,
        "deferred_count": deferred_count,
        "rejected_count": rejected_count,
        "fixed_search_limit": FIXED_SEARCH_LIMIT,
        "active_tab": active_tab,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    projects = store.list_projects()
    project = projects[0] if projects else None
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse(request=request, name="page.html", context=context)


@app.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, title: str = Form(...), description: str = Form("")):
    project = store.create_project(title, description)
    return _render_workspace(request, project, active_tab="search")


@app.post("/projects/{pid}/delete", response_class=HTMLResponse)
def delete_project(request: Request, pid: str):
    store.delete_project(pid)
    projects = store.list_projects()
    project = projects[0] if projects else None
    return _render_workspace(request, project, active_tab="search")


@app.get("/projects/{pid}/workspace", response_class=HTMLResponse)
def project_workspace(request: Request, pid: str, selected: str = "", tab: str = "search"):
    project = store.get(pid)
    return _render_workspace(request, project, selected_candidate_id=selected, active_tab=tab)


@app.post("/projects/{pid}/search", response_class=HTMLResponse)
def search_project(
    request: Request,
    pid: str,
    query: str = Form(...),
    selected_candidate_id: str = Form(""),
    active_tab: str = Form("search"),
    limit: Optional[int] = Form(default=None),
):
    project = store.get(pid)
    effective_limit = FIXED_SEARCH_LIMIT
    if limit is not None:
        try:
            effective_limit = FIXED_SEARCH_LIMIT if int(limit) <= 0 else min(int(limit), FIXED_SEARCH_LIMIT)
        except Exception:
            effective_limit = FIXED_SEARCH_LIMIT
    status_message = ""
    try:
        results = run_search(query, limit=effective_limit)
    except Exception as exc:
        results = []
        status_message = f"Search failed: {exc}"
    project.upsert_candidates(results, query=query)
    store.save(project)
    selected_candidate_id = results[0].candidate_id if results else selected_candidate_id
    return _render_workspace(
        request,
        project,
        query=query,
        status_message=status_message,
        selected_candidate_id=selected_candidate_id,
        active_tab="search",
    )


@app.post("/projects/{pid}/candidates/{cid}/decision", response_class=HTMLResponse)
def decide_candidate(
    request: Request,
    pid: str,
    cid: str,
    decision: str = Form(...),
    query: str = Form(""),
    active_tab: str = Form("search"),
):
    project = store.get(pid)
    candidate = project.set_decision(cid, Decision(decision))
    status_message = ""
    if candidate.decision == Decision.YES:
        update_graph_for_candidate(project, candidate)
        project.expansion_candidates = [
            item
            for item in project.expansion_candidates
            if item.candidate_id not in {cid, f"exp-{cid}"}
        ]
        status_message = "Accepted and added to the map."
    elif candidate.decision == Decision.NO:
        status_message = "Marked as rejected."
    elif candidate.decision == Decision.DEFER:
        status_message = "Deferred for later review."
    store.save(project)
    return _render_workspace(
        request,
        project,
        query=query,
        status_message=status_message,
        selected_candidate_id=cid,
        active_tab=active_tab,
    )


@app.post("/projects/{pid}/scan_map", response_class=HTMLResponse)
def scan_map_for_expansion(
    request: Request,
    pid: str,
    selected_candidate_id: str = Form(""),
    active_tab: str = Form("queue"),
    query: str = Form(""),
):
    project = store.get(pid)
    accepted = [candidate for candidate in reversed(project.candidates) if candidate.decision == Decision.YES]
    status_message = ""
    if not accepted:
        status_message = "Accept at least one paper before scanning the map for expansion suggestions."
        return _render_workspace(
            request,
            project,
            query=query,
            status_message=status_message,
            selected_candidate_id=selected_candidate_id,
            active_tab="queue",
        )

    total_added = 0
    for candidate in accepted[:SCAN_TARGET_LIMIT]:
        try:
            total_added += _merge_expansion_candidates(
                project,
                expand_from_candidate(candidate, limit=FIXED_SEARCH_LIMIT),
            )
        except Exception as exc:
            status_message = f"Expansion warning: {exc}"
            break
    if not status_message:
        status_message = f"Map scan complete. Added {total_added} queued suggestions."
    store.save(project)
    focus_id = selected_candidate_id or (accepted[0].candidate_id if accepted else "")
    return _render_workspace(
        request,
        project,
        query=query,
        status_message=status_message,
        selected_candidate_id=focus_id,
        active_tab="queue",
    )


@app.post("/projects/{pid}/upload_pdf", response_class=HTMLResponse)
def upload_pdf(
    request: Request,
    pid: str,
    cid: str = Form(...),
    active_tab: str = Form("retrieval"),
    query: str = Form(""),
    file: UploadFile = File(...),
):
    project = store.get(pid)
    library_dir = settings.library_dir
    candidate = project.get_candidate(cid)
    path = library_dir / Path(file.filename).name
    with open(path, "wb") as handle:
        handle.write(file.file.read())
    candidate.local_pdf_path = str(path)
    candidate.pdf_status = "manual"
    store.save(project)
    return _render_workspace(
        request,
        project,
        query=query,
        status_message="PDF uploaded.",
        selected_candidate_id=cid,
        active_tab=active_tab,
    )


@app.post("/projects/{pid}/upload_si", response_class=HTMLResponse)
def upload_si(
    request: Request,
    pid: str,
    cid: str = Form(...),
    active_tab: str = Form("retrieval"),
    query: str = Form(""),
    file: UploadFile = File(...),
):
    project = store.get(pid)
    library_dir = settings.library_dir
    candidate = project.get_candidate(cid)
    path = library_dir / f"SI_{Path(file.filename).name}"
    with open(path, "wb") as handle:
        handle.write(file.file.read())
    candidate.local_si_path = str(path)
    candidate.si_status = "manual"
    store.save(project)
    return _render_workspace(
        request,
        project,
        query=query,
        status_message="Supplementary file uploaded.",
        selected_candidate_id=cid,
        active_tab=active_tab,
    )


@app.post("/projects/{pid}/export")
def export_project(pid: str):
    project = store.get(pid)
    output_dir = settings.exports_dir / project.project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    papers_dir = output_dir / "papers"
    papers_dir.mkdir(exist_ok=True)
    import json
    import shutil

    metadata = []
    for candidate in project.candidates:
        if candidate.decision != "yes":
            continue
        if candidate.local_pdf_path:
            shutil.copy(candidate.local_pdf_path, papers_dir)
        metadata.append(
            {
                "title": candidate.title,
                "doi": candidate.doi,
                "pdf": candidate.local_pdf_path,
            }
        )
    with open(output_dir / "metadata.json", "w") as handle:
        json.dump(metadata, handle, indent=2)
    return "ok"
