from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r"", views.ProjectMapViewSet, basename="projectmap")

urlpatterns = [
    path("latest/", views.latest_project_map),
    path("events/", views.scan_events),
    path("<int:project_map_id>/view/<str:level>/", views.project_map_view),
    path("<int:project_map_id>/overlay/node/", views.upsert_node_overlay),
    path("<int:project_map_id>/tags/", views.project_tags),
    path("<int:project_map_id>/overlay/edge/", views.upsert_edge_overlay),
    path("<int:project_map_id>/lexicon/", views.lexicon_collection),
    path("<int:project_map_id>/lexicon/<str:term>/", views.delete_lexicon_entry),
    path("import/github/", views.import_from_github),
    path("<int:project_map_id>/sync-github/", views.sync_from_github),
    path("<int:project_map_id>/share/", views.manage_share),
    path("shared/", views.shared_projects),
    path("", include(router.urls)),
]
