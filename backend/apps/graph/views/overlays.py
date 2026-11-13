"""
@c3:component
name: Overlay Editing
container: Backend
technology: Python / Django REST Framework
description: Everything a human authors on top of the derived model — the node descriptions and edge labels a reader rewrites without touching the annotations, and the per-project lexicon that defines the terms those descriptions use. A scan replaces the model wholesale and never touches any of it, which is what keeps an enriched reading separable from the original one.
short_desc: Node and edge overlays, and the per-project lexicon
uses:
- Database/Database: "reads and writes the NodeOverlay, EdgeOverlay and LexiconEntry rows a reader authors"
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import EdgeOverlay, LexiconEntry, NodeOverlay, ProjectMap
from ..serializers import (
    EdgeOverlaySerializer,
    LexiconEntrySerializer,
    NodeOverlaySerializer,
)
from ._permissions import _require_auth, _require_owner


@api_view(["POST"])
def upsert_node_overlay(request, project_map_id):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err

    ser = NodeOverlaySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    d = ser.validated_data
    obj, _ = NodeOverlay.objects.get_or_create(
        project_map=pm,
        node_type=d["node_type"],
        system_name=d["system_name"],
        container_name=d["container_name"],
        node_name=d["node_name"],
    )
    obj.display_name = d["display_name"]
    obj.description = d["description"]
    obj.tags = d["tags"]
    obj.save()
    return Response({"ok": True})


@api_view(["POST"])
def upsert_edge_overlay(request, project_map_id):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err

    ser = EdgeOverlaySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    d = ser.validated_data
    obj, _ = EdgeOverlay.objects.get_or_create(project_map=pm, edge_id=d["edge_id"])
    obj.label = d["label"]
    obj.save()
    return Response({"ok": True})


@api_view(["GET", "POST"])
def lexicon_collection(request, project_map_id):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err
    if request.method == "GET":
        entries = pm.lexicon_entries.order_by("term")
        return Response([{"term": e.term, "definition": e.definition} for e in entries])
    # POST
    ser = LexiconEntrySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    term = ser.validated_data["term"]
    # Case-insensitive: re-adding "OSV" after "osv" already exists updates the
    # existing row instead of creating a near-duplicate glossary entry.
    entry = pm.lexicon_entries.filter(term__iexact=term).first()
    if entry is None:
        entry = LexiconEntry(project_map=pm, term=term)
    entry.definition = ser.validated_data["definition"]
    entry.save()
    return Response({"ok": True})


@api_view(["DELETE"])
def delete_lexicon_entry(request, project_map_id, term):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err
    entry = pm.lexicon_entries.filter(term__iexact=term).first()
    if entry is None:
        return Response(status=status.HTTP_404_NOT_FOUND)
    entry.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
