from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_workspace),
    path("<int:workspace_id>/", views.fetch_workspace),
    path("<int:workspace_id>/view/<str:level>/", views.workspace_view),
]
