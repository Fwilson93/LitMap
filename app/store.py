from pathlib import Path
from app.models import Project


class ProjectStore:
    def __init__(self, projects_dir, library_dir, exports_dir):
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.library_dir = library_dir
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir = exports_dir

    def path(self, pid):
        return self.projects_dir / f"{pid}.json"

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
            items.append(
                {
                    "candidate_id": c.candidate_id,
                    "title": c.title,
                    "pdf_status": c.pdf_status,
                    "si_status": c.si_status,
                    "doi": c.doi,
                }
            )
        return items
