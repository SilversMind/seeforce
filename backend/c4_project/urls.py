from django.urls import path, include

urlpatterns = [
    path("api/graph/", include("apps.graph.urls")),
]
