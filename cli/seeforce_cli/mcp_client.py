import httpx

from seeforce_cli.mcp_config import API_URL, http_headers, resolve_project_id


async def fetch_workspace() -> dict:
    """Return source_json for the configured project."""
    project_id = resolve_project_id()
    async with httpx.AsyncClient(base_url=API_URL, headers=http_headers(), timeout=15) as client:
        if project_id:
            r = await client.get("/api/graph/")
            r.raise_for_status()
            projects = r.json()
            if not isinstance(projects, list):
                projects = [projects]
            match_meta = next((p for p in projects if p.get("project_id") == project_id), None)
            if not match_meta and projects:
                match_meta = projects[0]
            if not match_meta:
                raise ValueError(f"No project found with id {project_id!r}")
            r2 = await client.get(f"/api/graph/{match_meta['id']}/")
            r2.raise_for_status()
            data = r2.json()
        else:
            r = await client.get("/api/graph/latest/")
            r.raise_for_status()
            data = r.json()

    return data.get("source_json", {})
