from __future__ import annotations
from pathlib import Path
from typing import Optional
import httpx
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
from app.providers.semantic_scholar import SemanticScholarProvider

settings=get_settings()
store=ProjectStore(settings.projects_dir,settings.library_dir,settings.exports_dir)
app=FastAPI(title=settings.app_name)

app.mount("/static",StaticFiles(directory=Path(__file__).resolve().parent/"static"),name="static")
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent/"templates"))
ss=SemanticScholarProvider()


def _ctx(pid:Optional[str]=None, scid:Optional[str]=None, mode:str="map"):
    ps=store.list_projects()
    p=store.get(pid) if pid else (ps[0] if ps else None)
    sc=None; r=[]
    if p:
        r=store.retrieval_items(p)
        if scid:
            try: sc=p.get_candidate(scid)
            except: sc=p.candidates[0] if p.candidates else None
        elif p.candidates: sc=p.candidates[0]
    g=render_graph_svg(p.graph if p else Graph(), scid)
    return {"request":None,"projects":ps,"project":p,"selected_candidate":sc,"retrieval_items":r,"graph_svg":g,"mode":mode}

def _resp(req,ctx): ctx["request"]=req; return templates.TemplateResponse(req,"partials/workspace_bundle.html",ctx)

@app.get("/",response_class=HTMLResponse)
def index(request:Request): return templates.TemplateResponse(request,"page.html",{**_ctx(),"request":request})

@app.post("/projects",response_class=HTMLResponse)
def create(request:Request,title:str=Form(...),description:str=Form("")):
    p=store.create_project(title,description); return _resp(request,_ctx(p.project_id))

@app.get("/projects/{pid}/workspace",response_class=HTMLResponse)
def workspace(request:Request,pid:str,mode:str="map"): return _resp(request,_ctx(pid,mode=mode))

@app.get("/projects/{pid}/retrieval",response_class=HTMLResponse)
def retrieval(request:Request,pid:str): return _resp(request,_ctx(pid,mode="retrieval"))

@app.post("/projects/{pid}/search",response_class=HTMLResponse)
def search(request:Request,pid:str,query:str=Form(...),limit:int=Form(8)):
    p=store.get(pid); res=run_search(query,limit)
    p.replace_candidates(res,query); store.save(p)
    return _resp(request,_ctx(pid,p.candidates[0].candidate_id if p.candidates else None))

@app.post("/projects/{pid}/candidates/{cid}/decision",response_class=HTMLResponse)
def decide(request:Request,pid:str,cid:str,decision:str=Form(...)):
    p=store.get(pid); d=Decision(decision)
    c=p.set_decision(cid,d)
    if d==Decision.YES:
        update_graph_for_candidate(p,c)
        p.add_expansion(expand_from_candidate(c))
    store.save(p); return _resp(request,_ctx(pid,cid))

@app.post("/projects/{pid}/expand/{cid}/accept",response_class=HTMLResponse)
def expand_accept(request:Request,pid:str,cid:str):
    p=store.get(pid); p.expansion_candidates=[x for x in p.expansion_candidates if x.candidate_id!=cid]
    store.save(p); return _resp(request,_ctx(pid))

@app.post("/projects/{pid}/expand/{cid}/ignore",response_class=HTMLResponse)
def expand_ignore(request:Request,pid:str,cid:str):
    p=store.get(pid); p.expansion_candidates=[x for x in p.expansion_candidates if x.candidate_id!=cid]
    store.save(p); return _resp(request,_ctx(pid))

@app.post("/projects/{pid}/expand/{cid}/blacklist",response_class=HTMLResponse)
def expand_blacklist(request:Request,pid:str,cid:str):
    p=store.get(pid); p.blacklist_item(cid); store.save(p)
    return _resp(request,_ctx(pid))

# REAL PDF RETRIEVAL
@app.post("/projects/{pid}/retrieval/auto",response_class=HTMLResponse)
def retrieval_auto(request:Request,pid:str):
    p=store.get(pid); lib=settings.library_dir; lib.mkdir(parents=True,exist_ok=True)

    for c in p.candidates:
        if not c.doi or c.local_pdf_present:
            continue
        meta=ss.fetch_graph(c.doi)
        pdf=(meta.get("openAccessPdf") or {}).get("url")
        if not pdf:
            continue
        try:
            r=httpx.get(pdf,timeout=15)
            r.raise_for_status()
            fpath=lib/f"{c.candidate_id}.pdf"
            with open(fpath,"wb") as f: f.write(r.content)
            c.local_pdf_present=True; c.local_pdf_path=str(fpath)
        except Exception:
            continue

    store.save(p); return _resp(request,_ctx(pid,mode="retrieval"))
