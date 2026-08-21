import json


def export_workspace(workspace: dict, indent: int = 2) -> str:
    return json.dumps(workspace, indent=indent, ensure_ascii=False)
