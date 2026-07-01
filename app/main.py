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

settings=get_settings()
store=ProjectStore(settings.projects_dir,settings.library_dir,settings.exports_dir)
app=FastAPI(title=settings.app_name)

app.mount("/static",StaticFiles(directory=Path(__file__).resolve().parent/"static"),name="static")
templates=Jinja2Templates(directory=str(Path(__file__).resolve().parent/"templates"))

def _ctx(pid:Optional[str]=None, scid:Optional[str]=None):
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
    return {"request":None,"projects":ps,"project":p,"selected_candidate":sc,"retrieval_items":r,"graph_svg":g,"export_dir":None}

def _resp(req,ctx): ctx["request"]=req; return templates.TemplateResponse(req,"partials/workspace_bundle.html",ctx)

@app.get("/",response_class=HTMLResponse)
def index(request:Request): return templates.TemplateResponse(request,"page.html",{**_ctx(),"request":request})

@app.post("/projects",response_class=HTMLResponse)
def create(request:Request,title:str=Form(...),description:str=Form("")):
    p=store.create_project(title,description)
    return _resp(request,_ctx(p.project_id))

@app.post("/projects/{pid}/search",response_class=HTMLResponse)
def search(request:Request,pid:str,query:str=Form(...),limit:int=Form(8)):
    p=store.get(pid)
    res=run_search(query,limit)
    p.replace_candidates(res,query)
    store.save(p)
    focus=p.candidates[0].candidate_id if p.candidates else None
    return _resp(request,_ctx(pid,focus))

@app.post("/projects/{pid}/candidates/{cid}/select",response_class=HTMLResponse)
def select(request:Request,pid:str,cid:str):
    return _resp(request,_ctx(pid,cid))

@app.post("/projects/{pid}/candidates/{cid}/decision",response_class=HTMLResponse)
def decide(request:Request,pid:str,cid:str,decision:str=Form(...),notes:str=Form("")):
    p=store.get(pid)
    try: d=Decision(decision)
    except: raise HTTPException(400,"Invalid decision")
    c=p.set_decision(cid,d,notes)
    if d==Decision.YES:
        update_graph_for_candidate(p,c)
        p.add_expansion([ExpansionCandidate(candidate_id=f"exp-{cid}",title=f"Related to: {c.title}",source=cid)])
    store.save(p)
    return _resp(request,_ctx(pid,cid))
