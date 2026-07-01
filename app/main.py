from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.search import run_search
from app.store import ProjectStore

settings = get_settings()
store = ProjectStore(settings.projects_dir, settings.library_dir, settings.exports_dir)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def _workspace_context(project=None, *, query: str = "", search_error: str = ""):
    projects = store.list_projects()
    return {
        "app_name": settings.app_name,
        "projects": projects,
        "project": project,
        "retrieval_items": store.retrieval_items(project) if project else [],
        "search_query": query,
        "search_error": search_error,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    projects = store.list_projects()
    project = projects[0] if projects else None
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="page.html",
        context=context,
    )


@app.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, title: str = Form(...), description: str = Form("")):
    project = store.create_project(title, description)
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


@app.get("/projects/{pid}/workspace", response_class=HTMLResponse)
def project_workspace(request: Request, pid: str):
    project = store.get(pid)
    context = _workspace_context(project)
    context["request"] = request
    return templates.TemplateResponse(
        request=request,
        name="partials/workspace_bundle.html",
        context=context,
    )


@app.post("/projects/{pid}/search", response_class=HTMLResponse)
def search_project(request: Request, pid: str, query: str = Form(...), limit: int = Form(12)):
    project = store.get(pid)
    search_error = ""
    try:
        results = run_search(query, limit=limit)
    except Exception as exc:
        results = []
        search_error = f"Search failed: {exc}"
    project.upsert_candidates(results, query=query)
    store.save(project)
    context = _workspace_context(project, query=query, search_error=search_error)
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
