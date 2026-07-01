from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from app.models import Candidate, Project, RetrievalItem, slugify


class ProjectStore:
    def __init__(self, projects_dir: Path, library_dir: Path, exports_dir: Path):
        self.projects_dir = projects_dir
        self.library_dir = library_dir
        self.exports_dir = exports_dir
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        (self.library_dir / 'pdfs').mkdir(parents=True, exist_ok=True)
        (self.library_dir / 'supplements').mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def project_path(self, project_id: str) -> Path:
        return self.projects_dir / f'{project_id}.json'

    def list_projects(self) -> list[Project]:
        projects = [Project.model_validate_json(path.read_text(encoding='utf-8')) for path in sorted(self.projects_dir.glob('*.json'))]
        return sorted(projects, key=lambda item: item.updated_at, reverse=True)

    def get(self, project_id: str) -> Project:
        path = self.project_path(project_id)
        if not path.exists():
            raise FileNotFoundError(project_id)
        return Project.model_validate_json(path.read_text(encoding='utf-8'))

    def save(self, project: Project) -> None:
        project.touch()
        self.project_path(project.project_id).write_text(project.model_dump_json(indent=2), encoding='utf-8')

    def create_project(self, title: str, description: str = '') -> Project:
        project = Project.create(title=title, description=description)
        base_id, suffix = project.project_id, 2
        while self.project_path(project.project_id).exists():
            project.project_id = f'{base_id}-{suffix}'
            suffix += 1
        self.save(project)
        return project

    def scan_library(self, project: Project) -> None:
        pdf_dir = self.library_dir / 'pdfs'
        supp_dir = self.library_dir / 'supplements'
        pdf_files = list(pdf_dir.iterdir()) if pdf_dir.exists() else []
        supp_files = list(supp_dir.iterdir()) if supp_dir.exists() else []
        for candidate in project.candidates:
            pdf_match = self._match_file(candidate, pdf_files)
            supp_match = self._match_file(candidate, supp_files)
            candidate.local_pdf_present = pdf_match is not None
            candidate.local_pdf_path = str(pdf_match.relative_to(self.library_dir)) if pdf_match else None
            candidate.local_supplement_present = supp_match is not None
            candidate.local_supplement_path = str(supp_match.relative_to(self.library_dir)) if supp_match else None
        project.add_event('library_scanned', 'Scanned managed library for candidate files.')
        self.save(project)

    def retrieval_items(self, project: Project) -> list[RetrievalItem]:
        items: list[RetrievalItem] = []
        for candidate in project.candidates:
            if candidate.decision != candidate.decision.YES:
                continue
            pdf_missing = not candidate.local_pdf_present
            supplement_missing = not candidate.local_supplement_present
            if not (pdf_missing or supplement_missing):
                continue
            hint = candidate.doi or candidate.title
            items.append(
                RetrievalItem(
                    candidate_id=candidate.candidate_id,
                    title=candidate.title,
                    pdf_missing=pdf_missing,
                    supplement_missing=supplement_missing,
                    lookup_hint=f'Search DOI/title: {hint}',
                )
            )
        return items

    def export_project(self, project: Project) -> Path:
        export_dir = self.exports_dir / project.project_id
        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / 'source_pdfs').mkdir(parents=True, exist_ok=True)
        manifest: dict[str, object] = {
            'project_id': project.project_id,
            'title': project.title,
            'accepted_count': sum(1 for candidate in project.candidates if candidate.decision == candidate.decision.YES),
            'items': [],
        }
        for candidate in project.candidates:
            if candidate.decision != candidate.decision.YES:
                continue
            record = {
                'candidate_id': candidate.candidate_id,
                'title': candidate.title,
                'doi': candidate.doi,
                'pdf': candidate.local_pdf_path,
                'supplement': candidate.local_supplement_path,
            }
            manifest['items'].append(record)
            if candidate.local_pdf_path:
                source = self.library_dir / candidate.local_pdf_path
                if source.exists():
                    target_name = f"{slugify(candidate.title)}{source.suffix.lower() or '.pdf'}"
                    shutil.copy2(source, export_dir / 'source_pdfs' / target_name)
        (export_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        project.add_event('project_exported', f'Exported accepted literature to {export_dir.name}.', export_dir=str(export_dir))
        self.save(project)
        return export_dir

    def _match_file(self, candidate: Candidate, file_paths: list[Path]) -> Optional[Path]:
        title_slug = slugify(candidate.title)
        doi_slug = slugify(candidate.doi or '') if candidate.doi else ''
        for path in file_paths:
            name = path.stem.lower()
            if title_slug and title_slug in slugify(name):
                return path
            if doi_slug and doi_slug in slugify(name):
                return path
        return None
