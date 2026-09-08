from django.urls import path, include, re_path
from django.views.generic import TemplateView
from apps.graph.views import use_share, share_view
from apps.graph.views.cli_auth import cli_auth
from apps.graph.views.github_app import github_app_setup
from apps.graph.views.install import serve_install_sh

urlpatterns = [
    path("cli/auth/", cli_auth),
    path("github-app/setup/", github_app_setup),
    path("install.sh", serve_install_sh),
    path("api/graph/", include("apps.graph.urls")),
    path("api/auth/", include("apps.graph.auth_urls")),
    path("api/share/<str:token>/", use_share),
    path("api/share/<str:token>/view/<str:level>/", share_view),
    path("accounts/", include("allauth.urls")),
    # Catch-all: serve React SPA for any non-API route
    re_path(r"^(?!api/|accounts/|assets/).*$", TemplateView.as_view(template_name="index.html")),
]
