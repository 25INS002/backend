from django.urls import path
from .views import UserProfileCreateView, UserProfileRetrieveView, UserProfileUpdateView

urlpatterns = [
    path("create/", UserProfileCreateView.as_view(), name="profile-create"),
    path("me/", UserProfileRetrieveView.as_view(), name="profile-me"),
    path("update/", UserProfileUpdateView.as_view(), name="profile-update"),
]
