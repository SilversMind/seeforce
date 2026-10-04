"""Preview URL conf: adds allauth's account pages back, since GitHub OAuth cannot reach a preview."""

from django.urls import include, path

from .urls import build_urlpatterns

urlpatterns = build_urlpatterns([path("accounts/", include("allauth.urls"))])
