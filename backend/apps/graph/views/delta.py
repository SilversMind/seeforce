"""
@c3:component
name: Delta View API
container: Backend
technology: Django REST Framework
description: Serves the architecture delta of a merge request — lists the linked repository's open pull requests, then for a chosen one reads .seeforce/workspace.json at the two commits it names, runs the comparison, and returns the decorated C1/C2/C3 view. Read-only — nothing is stored, no snapshot is kept per commit, and no cache is built. The repository is always read under the requesting user's own installation token, so access is decided by GitHub for the person actually looking rather than by the project's owner.
short_desc: Serves open pull requests and the decorated delta view
uses:
- GitHub Import: "reuses its installation-token resolution and its Contents API read of .seeforce/workspace.json at a commit"
- GitHub: "lists the repository's open pull requests through the Pulls API"
  technology: HTTPS
- Delta Reporter: "runs the comparison between the two commits' workspace snapshots"
- Delta Presenter: "projects that comparison onto the rendered view it returns"
- Graph transformer: "reads the project's node and edge overlays so a compared view carries the same authored labels as the ordinary one"
- Database/Project Store: "reads the ProjectMap row the comparison is requested for"
"""
import requests as http_requests
from c4parser.delta import diff
from c4parser.exceptions import C4ValidationError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..delta_presenter import decorate
from ..models import ProjectMap
from ..transformers import overlay_maps
from ._permissions import _require_access, _require_auth
from .github_import import _fetch_workspace_json, _get_contents, _github_token

_PULLS_URL = "https://api.github.com/repos/{repo}/pulls?state=open&per_page=50"
_JSON_ACCEPT = "application/vnd.github+json"


class _Refused(ValueError):
    """GitHub refused the requester's own access to the repository."""


class _SideMissing(ValueError):
    """One side of the comparison could not be read."""

    def __init__(self, side: str, message: str):
        self.side = side
        super().__init__(message)


def _get_json(url: str, token: str | None, repo: str):
    resp = _get_contents(url, token, _JSON_ACCEPT)
    # A public repo is served without auth, exactly as the contents read falls back.
    if token and resp.status_code in (401, 403, 404):
        resp = _get_contents(url, None, _JSON_ACCEPT)
    if resp.status_code in (401, 403):
        raise _Refused(f"Your GitHub App installation does not give you access to {repo}.")
    if resp.status_code == 404:
        raise _Refused(f"{repo} was not found, or it is private and not in your GitHub App installation.")
    if not resp.ok:
        raise ValueError(f"GitHub API error {resp.status_code}.")
    try:
        return resp.json()
    except ValueError:
        raise ValueError("GitHub returned a response that is not valid JSON.")


def _open_pull_requests(user, repo: str) -> list[dict]:
    """The repository's open pull requests, each carrying both commits the comparison needs."""
    token = _github_token(user, repo)
    return [
        {
            "number": pr["number"],
            "title": pr.get("title", ""),
            "head_ref": pr.get("head", {}).get("ref", ""),
            "base_ref": pr.get("base", {}).get("ref", ""),
            "head_sha": pr.get("head", {}).get("sha", ""),
            # ponytail: GitHub's recorded base, not a freshly computed merge base — it can lag on a long-lived branch; upgrade is one call to /compare for merge_base_commit.sha.
            "base_sha": pr.get("base", {}).get("sha", ""),
        }
        for pr in _get_json(_PULLS_URL.format(repo=repo), token, repo)
    ]


def _load_both(user, repo: str, option: dict) -> tuple[dict, dict]:
    """Read the committed baseline on each side, saying which side failed when one does."""
    token = _github_token(user, repo)
    loaded = {}
    for side in ("base", "head"):
        try:
            loaded[side] = _fetch_workspace_json(token, repo, option[f"{side}_sha"])
        except ValueError as exc:
            raise _SideMissing(side, str(exc))
    return loaded["base"], loaded["head"]


def _linked_project(request, project_map_id):
    """Resolve the project and refuse early: signed out, no access, or no repository to compare."""
    if err := _require_auth(request):
        return None, err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return None, Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_access(request, pm):
        return None, err
    if not pm.github_repo:
        return None, Response(
            {"error": "This project is not linked to a GitHub repository, so there is nothing to "
                      "compare. Link it from the project menu, or use `seeforce delta` locally."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return pm, None


@api_view(["GET"])
def project_pull_requests(request, project_map_id):
    pm, err = _linked_project(request, project_map_id)
    if err:
        return err
    try:
        return Response(_open_pull_requests(request.user, pm.github_repo))
    except _Refused as exc:
        return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except (ValueError, http_requests.RequestException) as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
def project_delta_view(request, project_map_id, level):
    pm, err = _linked_project(request, project_map_id)
    if err:
        return err

    requested = request.query_params.get("pr", "")
    if not requested.isdigit():
        return Response(
            {"error": "A pull request number is required, as ?pr=<number>."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        options = _open_pull_requests(request.user, pm.github_repo)
    except _Refused as exc:
        return Response({"error": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    except (ValueError, http_requests.RequestException) as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    option = next((o for o in options if o["number"] == int(requested)), None)
    if option is None:
        return Response(
            {"error": f"Pull request #{requested} is not open on {pm.github_repo} any more, so the "
                      "comparison cannot be built.", "missing": None},
            status=status.HTTP_409_CONFLICT,
        )

    try:
        base_ws, head_ws = _load_both(request.user, pm.github_repo, option)
    except _SideMissing as exc:
        return Response({"error": str(exc), "missing": exc.side}, status=status.HTTP_409_CONFLICT)
    except (ValueError, http_requests.RequestException) as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        delta = diff(base_ws, head_ws)
    except C4ValidationError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)

    node_overlay, edge_overlay = overlay_maps(pm)
    result = decorate(
        base_ws, head_ws, delta, level,
        request.query_params.get("system"), request.query_params.get("container"),
        node_overlay, edge_overlay,
    )
    result["comparison"] = option
    return Response(result)
