from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    data_dir: Path
    projects_dir: Path
    library_dir: Path
    exports_dir: Path
    app_name: str = "LitMap Slim"


def get_settings() -> Settings:
    explicit = os.getenv("LITMAP_DATA_DIR")
    repo_root = Path(__file__).resolve().parents[1]
    data_root = Path(explicit).resolve() if explicit else repo_root / "data"
    return Settings(
        repo_root=repo_root,
        data_dir=data_root,
        projects_dir=data_root / "projects",
        library_dir=data_root / "library",
        exports_dir=data_root / "exports",
    )
