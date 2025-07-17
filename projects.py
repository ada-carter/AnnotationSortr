"""
Project persistence functionality for tinySort application.
Handles loading, saving, and managing project configurations.
"""

import json
import pathlib
from typing import List, Dict

from config import PROJECTS_FILE

# ─────────────────────────────────────────────────────────────
# PROJECTS PERSISTENCE
# ─────────────────────────────────────────────────────────────
ProjectListType = List[Dict[str, str]]  # {"name":..., "path":..."}

def load_projects() -> ProjectListType:
    if PROJECTS_FILE.exists():
        try:
            with PROJECTS_FILE.open("r", encoding="utf8") as fh:
                data = json.load(fh)
            # sanity filter
            out: ProjectListType = []
            for obj in data if isinstance(data, list) else []:
                if not isinstance(obj, dict):
                    continue
                p = obj.get("path")
                n = obj.get("name") or ""
                if not isinstance(p, str):
                    continue
                out.append({"name": str(n), "path": p})
            return out
        except Exception:
            pass
    return []

def save_projects(projects: ProjectListType) -> None:
    try:
        with PROJECTS_FILE.open("w", encoding="utf8") as fh:
            json.dump(projects, fh, indent=2, sort_keys=False)
    except Exception:
        pass

def add_project(name: str, path_str: str) -> ProjectListType:
    projects = load_projects()
    # dedupe by path
    path_str = str(pathlib.Path(path_str).resolve())
    for p in projects:
        if pathlib.Path(p["path"]).resolve() == pathlib.Path(path_str):
            p["name"] = name  # update name
            save_projects(projects)
            return projects
    projects.append({"name": name, "path": path_str})
    save_projects(projects)
    return projects

def remove_project(path_str: str) -> ProjectListType:
    projects = load_projects()
    path_res = str(pathlib.Path(path_str).resolve())
    projects = [p for p in projects if pathlib.Path(p["path"]).resolve() != pathlib.Path(path_res)]
    save_projects(projects)
    return projects

def rename_project(path_str: str, new_name: str) -> ProjectListType:
    projects = load_projects()
    path_res = str(pathlib.Path(path_str).resolve())
    for p in projects:
        if pathlib.Path(p["path"]).resolve() == pathlib.Path(path_res):
            p["name"] = new_name
            break
    save_projects(projects)
    return projects
