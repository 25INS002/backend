from django.urls import path
from .views import MediaUploadView, MediaListView, MediaDeleteView

urlpatterns = [
    path("upload/", MediaUploadView.as_view(), name="media-upload"),
    path("list/", MediaListView.as_view(), name="media-list"),
    path("delete/<int:pk>/", MediaDeleteView.as_view(), name="media-delete"),
]
