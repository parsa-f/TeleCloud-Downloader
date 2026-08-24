"""
github_upload.py - Upload a file to the user's OWN GitHub repo using their
personal token (stored per-user in Postgres). Returns the raw download link.
"""

import os
from github import Github
from config import GITHUB_DEFAULT_REPO
import db


def upload_to_github(file_path: str, user_id: int, status_msg=None) -> str | None:
    """Upload file_path to the user's GitHub repo, return raw URL or None."""
    token = db.get_github_token(user_id)
    if not token:
        return None
    repo = db.get_github_repo(user_id) or GITHUB_DEFAULT_REPO
    if not repo:
        return None

    fname = os.path.basename(file_path)
    try:
        gh = Github(token)
        repository = gh.get_repo(repo)
        with open(file_path, "rb") as f:
            content = f.read()
        path = f"uploads/{user_id}/{fname}"
        try:
            existing = repository.get_contents(path)
            repository.update_file(path, f"upload {fname}", content, existing.sha)
        except Exception:
            repository.create_file(path, f"upload {fname}", content)
        # raw link
        return f"https://raw.githubusercontent.com/{repo}/main/{path}"
    except Exception as e:
        print(f"[github] upload failed for user {user_id}: {e}")
        return None
