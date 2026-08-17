from django.urls import path, include

urlpatterns = [
    path("api/graph/", include("apps.graph.urls")),
    path("api/auth/", include("apps.graph.auth_urls")),
    path("accounts/", include("allauth.urls")),
]
