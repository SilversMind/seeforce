from django.urls import path, include, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path("api/graph/", include("apps.graph.urls")),
    path("api/auth/", include("apps.graph.auth_urls")),
    path("accounts/", include("allauth.urls")),
    # Catch-all: serve React SPA for any non-API route
    re_path(r"^(?!api/|accounts/|assets/).*$", TemplateView.as_view(template_name="index.html")),
]
