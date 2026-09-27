"""
@c3:component
name: GitHub Import
container: Backend
description: Imports, re-syncs, and links project architecture to GitHub repositories. Repo access is scoped per user by matching the repo's owner login against their GitHub App installations (a user may have several — personal + org); GitHub App Token Manager mints an installation token for the matching install, falling back to their newest installation, then to an unauthenticated request for public repos with no install. Fetches .seeforce/workspace.json via the GitHub Contents API and upserts it as a ProjectMap. Blob links are built client-side from github_repo/github_branch, not here.
short_desc: Imports, re-syncs, and links project architecture from GitHub
uses:
  - GitHub: "Fetches .seeforce/workspace.json via GitHub Contents API, authenticated with an installation token when one covers the repo, unauthenticated otherwise"
    technology: HTTPS
  - GitHub App Token Manager: "Requests a fresh installation token before each Contents API call"
  - Database: "creates or updates the ProjectMap row for the imported, synced, or linked repo"
"""

import json

import requests as http_requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django.utils import timezone

from ..models import ProjectMap, sync_lexicon_entries
from ._permissions import _require_auth, _require_owner


def _github_token(user, repo: str = ""):
    from ..github_app import GitHubAppTokenManager
    installations = user.github_app_installations
    # A user can have several installations (personal + org); pick the one owning
    # this repo, falling back to the newest for the single-installation case.
    installation = None
    if repo:
        installation = installations.filter(account_login__iexact=repo.split("/")[0]).first()
    installation = installation or installations.order_by("-created_at").first()
    if installation is None:
        return None
    try:
        return GitHubAppTokenManager().installation_token(installation.installation_id)
    except http_requests.RequestException:
        raise ValueError(
            "GitHub App installation token could not be minted — the installation "
            "may have been revoked. Reinstall the GitHub App."
        )


def _get_contents(url: str, token: str | None) -> "http_requests.Response":
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        return http_requests.get(url, headers=headers, timeout=10)
    except http_requests.RequestException as exc:
        raise ValueError(f"Could not reach GitHub: {exc}")


def _fetch_workspace_json(token: str | None, repo: str, branch: str) -> dict:
    """
    Fetch .seeforce/workspace.json from a GitHub repo.
    Raises ValueError with a user-facing message on any failure.
    """
    url = f"https://api.github.com/repos/{repo}/contents/.seeforce/workspace.json?ref={branch}"
    resp = _get_contents(url, token)

    # No installation covers this repo, or the installation doesn't include it —
    # it might still be a public repo, which GitHub serves without auth.
    # ponytail: unauthenticated fallback shares this server's IP rate limit
    # (60 req/h) across every user; swap in a low-privilege PAT if that bites.
    if token and resp.status_code in (401, 403, 404):
        resp = _get_contents(url, None)

    if resp.status_code == 404:
        raise ValueError(
            f"No .seeforce/workspace.json found in {repo}@{branch}, or {repo} is private "
            "and not accessible. Either run 'just scan' in that repo, or check that this "
            "repo is included in your GitHub App installation."
        )
    if resp.status_code == 401:
        raise ValueError("GitHub App installation token expired or invalid. Reinstall the GitHub App.")
    if resp.status_code == 403:
        raise ValueError(
            f"Access denied to {repo}. Make sure this repo is included in your GitHub App installation."
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

    try:
        token = _github_token(request.user, repo)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        workspace = _fetch_workspace_json(token, repo, branch)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    project_id = f"github:{repo}"
    # GitHub owner/repo are case-insensitive, so reuse a row that only differs in case.
    existing = ProjectMap.objects.filter(project_id__iexact=project_id).first()
    if existing:
        project_id = existing.project_id
    pm, created = ProjectMap.objects.update_or_create(
        project_id=project_id,
        defaults={
            "name": name,
            "source_json": workspace,
            "owner": request.user,
            "github_repo": repo,
            "github_branch": branch,
            "last_synced_at": timezone.now(),
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
    if ProjectMap.objects.filter(project_id__iexact=project_id).exclude(id=pm.id).exists():
        return Response(
            {"error": f"{repo} is already imported as a separate project."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        token = _github_token(request.user, repo)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        workspace = _fetch_workspace_json(token, repo, branch)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    pm.project_id = project_id
    pm.github_repo = repo
    pm.github_branch = branch
    pm.source_json = workspace
    pm.last_synced_at = timezone.now()
    pm.save(update_fields=["project_id", "github_repo", "github_branch", "source_json", "last_synced_at", "updated_at"])
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

    try:
        token = _github_token(request.user, pm.github_repo)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        workspace = _fetch_workspace_json(token, pm.github_repo, pm.github_branch)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    pm.source_json = workspace
    pm.last_synced_at = timezone.now()
    pm.save(update_fields=["source_json", "last_synced_at", "updated_at"])
    sync_lexicon_entries(pm, workspace)

    return Response({"id": pm.id, "name": pm.name, "synced": True, "last_synced_at": pm.last_synced_at})
