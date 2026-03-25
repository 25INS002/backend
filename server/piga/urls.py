from django.urls import path
from . import views

urlpatterns = [
    # ——— User Endpoints ———
    path("submit/", views.PigaSubmitView.as_view(), name="piga-submit"),
    path("my-applications/", views.MyPigaListView.as_view(), name="piga-my-list"),
    path("my-applications/<int:pk>/", views.MyPigaDetailView.as_view(), name="piga-my-detail"),
    path("my-applications/<int:pk>/update/", views.MyPigaUpdateView.as_view(), name="piga-my-update"),
    path("my-statistics/", views.MyPigaStatisticsView.as_view(), name="piga-my-stats"),
    path("<int:pk>/remarks/", views.append_piga_remark, name="piga-remark"),

    # ——— Admin Endpoints ———
    path("admin/applications/", views.AdminPigaListView.as_view(), name="piga-admin-list"),
    path("admin/applications/<int:pk>/", views.AdminPigaDetailView.as_view(), name="piga-admin-detail"),
    path("admin/applications/<int:pk>/update/", views.AdminPigaUpdateView.as_view(), name="piga-admin-update"),
    path("admin/statistics/", views.AdminPigaStatisticsView.as_view(), name="piga-admin-stats"),
]
