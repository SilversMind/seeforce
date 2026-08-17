from django.urls import path
from apps.graph import views

urlpatterns = [
    path("me/", views.auth_me),
    path("logout/", views.auth_logout),
]
