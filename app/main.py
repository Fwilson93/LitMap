from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.store import ProjectStore
from app.config import get_settings
from app.models import slugify_filename, RetrievalStatus
import webbrowser
from pathlib import Path

settings = get_settings()
store = ProjectStore(settings.projects_dir, settings.library_dir, settings.exports_dir)
app = FastAPI()

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.post("/projects/{pid}/retrieval/auto")
def retrieval_auto(pid:str):
    p = store.get(pid)
    lib = settings.library_dir

    for c in p.candidates:
        if not c.doi or c.pdf_status != RetrievalStatus.MISSING:
            continue
        try:
            filename = slugify_filename(c)
            path = lib/filename
            with open(path, "wb") as f:
                f.write(b"
")
            c.pdf_status = RetrievalStatus.AUTO
            c.local_pdf_path = str(path)
        except:
            c.pdf_status = RetrievalStatus.FAILED

    store.save(p)
    return "ok"

@app.post("/projects/{pid}/retrieval/open")
def open_paper(pid:str, doi:str=Form(...)):
    url = f"https://doi.org/{doi}"
    webbrowser.open(url)
    return "ok"

@app.post("/projects/{pid}/retrieval/mark")
def mark_manual(pid:str, cid:str=Form(...)):
    p = store.get(pid)
    for c in p.candidates:
        if c.candidate_id == cid:
            c.pdf_status = RetrievalStatus.MANUAL
    store.save(p)
    return "ok"
