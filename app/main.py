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


def _resolve_selected_candidate(project, selected_candidate_id: str = ""):
    if not project or not project.candidates:
        return None
    if selected_candidate_id:
        try:
            return project.get_candidate(selected_candidate_id)
        except KeyError:
            pass
    return project.candidates[0]


def _merge_expansion_candidates(project, incoming) -> None:
    accepted_ids = {candidate.candidate_id for candidate in project.candidates}
    seen = {candidate.candidate_id for candidate in project.expansion_candidates}
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


def _workspace_context(
    project=None,
    *,
    query: str = "",
    search_error: str = "",
    selected_candidate_id: str = "",
):
    projects = store.list_projects()
    selected_candidate = _resolve_selected_candidate(project, selected_candidate_id)
    graph_svg = ""
    if project:
        graph_svg = render_graph_svg(
            project.graph,
            selected_candidate.candidate_id if selected_candidate else None,
            project.project_id,
        )

    accepted_count = 0
    deferred_count = 0
    rejected_count = 0
    if project:
        accepted_count = sum(
            1 for candidate in project.candidates if candidate.decision == Decision.YES
        )
        deferred_count = sum(
            1 for candidate in project.candidates if candidate.decision == Decision.DEFER
        )
        rejected_count = sum(
            1 for candidate in project.candidates if candidate.decision == Decision.NO
        )

    return {
        "app_name": settings.app_name,
        "projects": projects,
        "project": project,
        "retrieval_items": store.retrieval_items(project) if project else [],
        "search_query": query,
        "search_error": search_error,
        "selected_candidate": selected_candidate,
        "selected_candidate_id": selected_candidate.candidate_id if selected_candidate else "",
        "graph_svg": graph_svg,
        "accepted_count": accepted_count,
        "deferred_count": deferred_count,
        "rejected_count": rejected_count,
        "fixed_search_limit": FIXED_SEARCH_LIMIT,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    projects = store.list_projects()
    project = projects[0] if projects else None
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse(request=request, name="page.html", context=context)


@app.post("/projects", response_class=HTMLResponse)
def create_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
):
    project = store.create_project(title, description)
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


@app.post("/projects/{pid}/delete", response_class=HTMLResponse)
def delete_project(request: Request, pid: str):
    store.delete_project(pid)
    projects = store.list_projects()
    project = projects[0] if projects else None
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


@app.get("/projects/{pid}/workspace", response_class=HTMLResponse)
def project_workspace(request: Request, pid: str, selected: str = ""):
    project = store.get(pid)
    context = _workspace_context(project, selected_candidate_id=selected)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


@app.post("/projects/{pid}/search", response_class=HTMLResponse)
def search_project(
    request: Request,
    pid: str,
    query: str = Form(...),
    limit: Optional[int] = Form(default=None),
):
    project = store.get(pid)
    search_error = ""
    effective_limit = FIXED_SEARCH_LIMIT

    if limit is not None:
        try:
            effective_limit = (
                FIXED_SEARCH_LIMIT
                if int(limit) <= 0
                else min(int(limit), FIXED_SEARCH_LIMIT)
            )
        except Exception:
            effective_limit = FIXED_SEARCH_LIMIT

    try:
        results = run_search(query, limit=effective_limit)
    except Exception as exc:
        results = []
        search_error = f"Search failed: {exc}"

    project.upsert_candidates(results, query=query)
    store.save(project)

    selected_candidate_id = results[0].candidate_id if results else ""
    context = _workspace_context(
        project,
        query=query,
        search_error=search_error,
        selected_candidate_id=selected_candidate_id,
    )
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


@app.post("/projects/{pid}/candidates/{cid}/decision", response_class=HTMLResponse)
def decide_candidate(
    request: Request,
    pid: str,
    cid: str,
    decision: str = Form(...),
    query: str = Form(""),
):
    project = store.get(pid)
    candidate = project.set_decision(cid, Decision(decision))
    search_error = ""

    if candidate.decision == Decision.YES:
        update_graph_for_candidate(project, candidate)
        try:
            expanded = expand_from_candidate(candidate, limit=FIXED_SEARCH_LIMIT)
        except Exception as exc:
            expanded = []
            search_error = f"Expansion warning: {exc}"

        _merge_expansion_candidates(project, expanded)
        project.expansion_candidates = [
            item
            for item in project.expansion_candidates
            if item.candidate_id not in {cid, f"exp-{cid}"}
        ]

    store.save(project)

    context = _workspace_context(
        project,
        query=query,
        search_error=search_error,
        selected_candidate_id=cid,
    )
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


@app.post("/projects/{pid}/upload_pdf")
def upload_pdf(pid: str, cid: str = Form(...), file: UploadFile = File(...)):
    project = store.get(pid)
    library_dir = settings.library_dir
    candidate = project.get_candidate(cid)
    path = library_dir / Path(file.filename).name

    with open(path, "wb") as handle:
        handle.write(file.file.read())

    candidate.local_pdf_path = str(path)
    candidate.pdf_status = "manual"
    store.save(project)
    return "ok"


@app.post("/projects/{pid}/upload_si")
def upload_si(pid: str, cid: str = Form(...), file: UploadFile = File(...)):
    project = store.get(pid)
    library_dir = settings.library_dir
    candidate = project.get_candidate(cid)
    path = library_dir / f"SI_{Path(file.filename).name}"

    with open(path, "wb") as handle:
        handle.write(file.file.read())

    candidate.local_si_path = str(path)
    candidate.si_status = "manual"
    store.save(project)
    return "ok"


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
