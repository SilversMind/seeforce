from apps.graph.views import share_lexicon, share_tags, share_view, use_share
from apps.graph.views.cli_auth import cli_auth
from apps.graph.views.github_app import github_app_setup
from apps.graph.views.install import serve_install_sh
from django.urls import include, path, re_path
from django.views.generic import RedirectView, TemplateView

# Only the GitHub flow; allauth.account's login, signup and password pages stay unrouted.
GITHUB_ONLY_ACCOUNT_URLS = [
    # NOTE: socialaccount/views.py reverses account_login, so the name must resolve or GitHub
    # signup 500s; redirecting keeps the name alive without serving a password form.
    path(
        "accounts/login/",
        RedirectView.as_view(pattern_name="github_login", query_string=True),
        name="account_login",
    ),
    # Mounted exactly where allauth.urls puts them, so previews and production agree.
    path("accounts/3rdparty/", include("allauth.socialaccount.urls")),
    path("accounts/", include("allauth.socialaccount.providers.github.urls")),
]


def build_urlpatterns(account_urls):
    """Assembles the URL conf around the chosen account routes; preview_urls reuses it."""
    return [
        path("cli/auth/", cli_auth),
        path("github-app/setup/", github_app_setup),
        path("install.sh", serve_install_sh),
        path("api/graph/", include("apps.graph.urls")),
        path("api/auth/", include("apps.graph.auth_urls")),
        path("api/share/<str:token>/", use_share),
        path("api/share/<str:token>/view/<str:level>/", share_view),
        path("api/share/<str:token>/lexicon/", share_lexicon),
        path("api/share/<str:token>/tags/", share_tags),
        *account_urls,
        # Catch-all: serve React SPA for any non-API route
        re_path(r"^(?!api/|accounts/|assets/).*$", TemplateView.as_view(template_name="index.html")),
    ]


urlpatterns = build_urlpatterns(GITHUB_ONLY_ACCOUNT_URLS)
