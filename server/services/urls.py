from django.urls import path
from . import views

urlpatterns = [
    # --- Service URLs ---
    path('list/', views.ServiceListView.as_view(), name='service-list'),
    path('create/', views.ServiceCreateView.as_view(), name='service-create'),
    path('<int:pk>/', views.ServiceRetrieveView.as_view(), name='service-detail'),
    path('<int:pk>/update/', views.ServiceUpdateView.as_view(), name='service-update'),
    path('<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service-delete'),

    # --- Nested Availability URLs ---
    path('<int:service_pk>/availability/', views.AvailabilityListCreateView.as_view(), name='availability-list-create'),
    path('<int:service_pk>/availability/<int:pk>/', views.AvailabilityDetailView.as_view(), name='availability-detail'),

    # --- Service Request URLs for Regular Users ---
    path('requests/create/', views.ServiceRequestCreateView.as_view(), name='request-create'),
    path('my-requests/', views.MyServiceRequestListView.as_view(), name='my-requests-list'),

    # --- Service Request URLs for Admins ---
    path('admin/requests/', views.AdminServiceRequestListView.as_view(), name='admin-requests-list'),
    path('admin/requests/<int:pk>/update/', views.AdminServiceRequestUpdateView.as_view(), name='admin-request-update'),
]