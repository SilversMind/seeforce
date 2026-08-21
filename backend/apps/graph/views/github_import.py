"""
@c3:component
name: GitHub Import
container: Backend
description: Imports and re-syncs project architecture from GitHub repositories — fetches .seeforce/workspace.json via the GitHub Contents API using the user's stored OAuth token and stores it as a ProjectMap; also resolves source file paths to clickable GitHub blob links.
uses:
  - GitHub: "Fetches .seeforce/workspace.json via GitHub Contents API using stored OAuth token"
    technology: HTTPS
"""

import json

import requests as http_requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import ProjectMap, sync_lexicon_entries
from ._permissions import _require_auth, _require_owner


def _github_token(user):
    from allauth.socialaccount.models import SocialToken
    token = SocialToken.objects.filter(account__user=user, account__provider="github").first()
    return token.token if token else None


def _fetch_workspace_json(token: str, repo: str, branch: str) -> dict:
    """
    Fetch .seeforce/workspace.json from a GitHub repo.
    Raises ValueError with a user-facing message on any failure.
    """
    url = f"https://api.github.com/repos/{repo}/contents/.seeforce/workspace.json?ref={branch}"
    try:
        resp = http_requests.get(url, headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3.raw",
        }, timeout=10)
    except http_requests.RequestException as exc:
        raise ValueError(f"Could not reach GitHub: {exc}")

    if resp.status_code == 404:
        raise ValueError(
            f"No .seeforce/workspace.json found in {repo}@{branch}. "
            "Run 'just scan' in that repo first to generate it."
        )
    if resp.status_code == 401:
        raise ValueError("GitHub token expired or lacks repo access. Log out and log back in.")
    if resp.status_code == 403:
        raise ValueError(
            f"Access denied to {repo}. For private repos, make sure you granted repo access during login."
        )
    if not resp.ok:
        raise ValueError(f"GitHub API error {resp.status_code}.")

    try:
        return resp.json()
    except json.JSONDecodeError:
        raise ValueError(".seeforce/workspace.json is not valid JSON.")


@api_view(["POST"])
def import_from_github(request):
    if err := _require_auth(request):
        return err

    repo = (request.data.get("repo") or "").strip().strip("/")
    branch = (request.data.get("branch") or "main").strip()
    name = (request.data.get("name") or "").strip() or repo.split("/")[-1]

    if not repo or repo.count("/") != 1:
        return Response({"error": "repo must be 'owner/repo'"}, status=status.HTTP_400_BAD_REQUEST)

    token = _github_token(request.user)
    if not token:
        return Response(
            {"error": "GitHub account not connected. Log out and log back in with GitHub."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        workspace = _fetch_workspace_json(token, repo, branch)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    project_id = f"github:{repo}"
    pm, created = ProjectMap.objects.update_or_create(
        project_id=project_id,
        defaults={
            "name": name,
            "source_json": workspace,
            "owner": request.user,
            "github_repo": repo,
            "github_branch": branch,
        },
    )
    sync_lexicon_entries(pm, workspace)

    return Response(
        {"id": pm.id, "name": pm.name, "created": created},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
def link_to_github(request, project_map_id):
    """Attach an existing (e.g. upload-created) ProjectMap to a GitHub repo
    in place, so it becomes sync-able going forward instead of requiring a
    second, separate project to be created via import_from_github."""
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err

    if pm.github_repo:
        return Response(
            {"error": "This project is already linked to a GitHub repo."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    repo = (request.data.get("repo") or "").strip().strip("/")
    branch = (request.data.get("branch") or "main").strip()
    if not repo or repo.count("/") != 1:
        return Response({"error": "repo must be 'owner/repo'"}, status=status.HTTP_400_BAD_REQUEST)

    project_id = f"github:{repo}"
    if ProjectMap.objects.filter(project_id=project_id).exclude(id=pm.id).exists():
        return Response(
            {"error": f"{repo} is already imported as a separate project."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token = _github_token(request.user)
    if not token:
        return Response(
            {"error": "GitHub account not connected. Log out and log back in with GitHub."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        workspace = _fetch_workspace_json(token, repo, branch)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    pm.project_id = project_id
    pm.github_repo = repo
    pm.github_branch = branch
    pm.source_json = workspace
    pm.save(update_fields=["project_id", "github_repo", "github_branch", "source_json", "updated_at"])
    sync_lexicon_entries(pm, workspace)

    return Response({"id": pm.id, "name": pm.name, "linked": True})


@api_view(["POST"])
def sync_from_github(request, project_map_id):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err

    if not pm.github_repo:
        return Response(
            {"error": "This project was not imported from GitHub."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token = _github_token(request.user)
    if not token:
        return Response(
            {"error": "GitHub account not connected. Log out and log back in with GitHub."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        workspace = _fetch_workspace_json(token, pm.github_repo, pm.github_branch)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    pm.source_json = workspace
    pm.save(update_fields=["source_json", "updated_at"])
    sync_lexicon_entries(pm, workspace)

    return Response({"id": pm.id, "name": pm.name, "synced": True})
