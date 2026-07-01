from fastapi import FastAPI, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.store import ProjectStore
from app.config import get_settings

settings=get_settings()
store=ProjectStore(settings.projects_dir,settings.library_dir,settings.exports_dir)
app=FastAPI()

templates=Jinja2Templates(directory="app/templates")
app.mount("/static",StaticFiles(directory="app/static"),name="static")

@app.post("/projects/{pid}/upload_pdf")
def upload_pdf(pid:str,cid:str=Form(...),file:UploadFile=File(...)):
    p=store.get(pid); lib=settings.library_dir
    c=p.get_candidate(cid)
    path=lib/file.filename
    with open(path,"wb") as f: f.write(file.file.read())
    c.local_pdf_path=str(path); c.pdf_status="manual"
    store.save(p); return "ok"

@app.post("/projects/{pid}/upload_si")
def upload_si(pid:str,cid:str=Form(...),file:UploadFile=File(...)):
    p=store.get(pid); lib=settings.library_dir
    c=p.get_candidate(cid)
    path=lib/("SI_"+file.filename)
    with open(path,"wb") as f: f.write(file.file.read())
    c.local_si_path=str(path); c.si_status="manual"
    store.save(p); return "ok"

@app.post("/projects/{pid}/export")
def export_project(pid:str):
    p=store.get(pid); out=settings.exports_dir/p.project_id
    out.mkdir(parents=True,exist_ok=True)
    papers=out/"papers"; papers.mkdir(exist_ok=True)

    import json

    meta=[]
    for c in p.candidates:
        if c.decision!="yes": continue
        if c.local_pdf_path:
            import shutil
            shutil.copy(c.local_pdf_path,papers)
        meta.append({
            "title":c.title,
            "doi":c.doi,
            "pdf":c.local_pdf_path
        })

    with open(out/"metadata.json","w") as f: json.dump(meta,f,indent=2)

    return "ok"
