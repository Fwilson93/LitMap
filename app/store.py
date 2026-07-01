from app.models import Project


class ProjectStore:
    def __init__(self, projects_dir, library_dir, exports_dir):
        self.projects_dir = projects_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.library_dir = library_dir
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir = exports_dir
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def path(self, pid):
        return self.projects_dir / f"{pid}.json"

    def create_project(self, title, description=""):
        project = Project.create(title, description)
        self.save(project)
        return project

    def list_projects(self):
        projects = []
        for path in sorted(self.projects_dir.glob("*.json")):
            try:
                projects.append(Project.model_validate_json(path.read_text()))
            except Exception:
                continue
        projects.sort(key=lambda item: item.updated_at, reverse=True)
        return projects

    def get(self, pid):
        return Project.model_validate_json(self.path(pid).read_text())

    def save(self, project):
        project.touch()
        self.path(project.project_id).write_text(project.model_dump_json(indent=2))

    def retrieval_items(self, project):
        items = []
        for candidate in project.candidates:
            items.append(
                {
                    "candidate_id": candidate.candidate_id,
                    "title": candidate.title,
                    "pdf_status": candidate.pdf_status,
                    "si_status": candidate.si_status,
                    "doi": candidate.doi,
                }
            )
        return items
