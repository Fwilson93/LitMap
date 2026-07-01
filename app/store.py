from pathlib import Path
from app.models import Project, RetrievalItem
import json

class ProjectStore:
    def __init__(self, projects_dir, library_dir, exports_dir):
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.library_dir = library_dir
        self.exports_dir = exports_dir

    def path(self, pid):
        return self.projects_dir / f'{pid}.json'

    def list_projects(self):
        projects = []
        for p in self.projects_dir.glob('*.json'):
            try:
                projects.append(Project.model_validate_json(p.read_text()))
            except Exception:
                continue
        return projects

    def create_project(self, title, description=""):
        p = Project.create(title, description)
        self.save(p)
        return p

    def get(self, pid):
        return Project.model_validate_json(self.path(pid).read_text())

    def save(self, p):
        self.path(p.project_id).write_text(p.model_dump_json())

    def retrieval_items(self, project):
        items = []
        for c in project.candidates:
            items.append(RetrievalItem(
                candidate_id=c.candidate_id,
                title=c.title,
                pdf_missing=not c.local_pdf_present,
                supplement_missing=not c.local_supplement_present,
                lookup_hint=c.doi or c.title
            ))
        return items
