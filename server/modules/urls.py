from django.urls import path
from .views import (
    ModuleCreateView, ModuleListView, ModuleUpdateView, ModuleDeleteView,
    AssignModuleAccessView, ListAdminModulesView
)

urlpatterns = [
    path("create/", ModuleCreateView.as_view(), name="create-module"),
    path("list/", ModuleListView.as_view(), name="list-modules"),
    path("update/<int:pk>/", ModuleUpdateView.as_view(), name="update-module"),
    path("delete/<int:pk>/", ModuleDeleteView.as_view(), name="delete-module"),
    path("assign-access/", AssignModuleAccessView.as_view(), name="assign-access"),
    path("admin-access/", ListAdminModulesView.as_view(), name="list-admin-access"),
]
