from django.urls import path
from .views import CreateAdminView, ListUsersView, UpdateUserView, DeleteUserView

urlpatterns = [
    path("create-admin/", CreateAdminView.as_view(), name="create-admin"),
    path("list-users/", ListUsersView.as_view(), name="list-users"),
    path("update-user/<int:pk>/", UpdateUserView.as_view(), name="update-user"),
    path("delete-user/<int:pk>/", DeleteUserView.as_view(), name="delete-user"),
]
