from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_project_maps),
    path("upload/", views.upload_project_map),
    path("latest/", views.latest_project_map),
    path("events/", views.scan_events),
    path("<int:project_map_id>/", views.fetch_project_map),
    path("<int:project_map_id>/view/<str:level>/", views.project_map_view),
    path("<int:project_map_id>/overlay/node/", views.upsert_node_overlay),
    path("<int:project_map_id>/overlay/edge/", views.upsert_edge_overlay),
]
