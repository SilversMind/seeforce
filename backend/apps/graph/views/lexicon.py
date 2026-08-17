from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import ProjectMap, LexiconEntry
from ..serializers import LexiconEntrySerializer
from ._permissions import _require_auth, _require_owner


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
    entry, _ = LexiconEntry.objects.get_or_create(
        project_map=pm, term=ser.validated_data["term"]
    )
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
    try:
        entry = LexiconEntry.objects.get(project_map=pm, term=term)
    except LexiconEntry.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    entry.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
