from django.urls import path
from . import views

urlpatterns = [
    # Service URLs
    path('list/', views.ServiceListView.as_view(), name='service-list'),
    path('create/', views.ServiceCreateView.as_view(), name='service-create'),
    path('<int:pk>/', views.ServiceRetrieveView.as_view(), name='service-detail'),
    path('<int:pk>/update/', views.ServiceUpdateView.as_view(), name='service-update'),
    path('<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service-delete'),
    path('search/', views.ServiceSearchView.as_view(), name='service-search'),
    path('<int:service_pk>/plans/', views.service_plans, name='service-plans'),
    path('<int:service_pk>/check-availability/', views.check_service_availability, name='check-availability'),
    path('<int:service_pk>/statistics/', views.service_statistics, name='service-statistics'),
    
    # Availability URLs
    path('<int:service_pk>/availability/', views.AvailabilityListCreateView.as_view(), name='availability-list-create'),
    path('<int:service_pk>/availability/<int:pk>/', views.AvailabilityDetailView.as_view(), name='availability-detail'),
    path('<int:service_pk>/availability/bulk/', views.BulkAvailabilityUpdateView.as_view(), name='availability-bulk-update'),
    
    # Service Request URLs
    path('requests/create/', views.ServiceRequestCreateView.as_view(), name='request-create'),
    path('requests/my-requests/', views.MyServiceRequestListView.as_view(), name='my-requests'),
    path('requests/my-requests/<int:pk>/', views.MyServiceRequestDetailView.as_view(), name='my-request-detail'),
    path('requests/my-requests/<int:pk>/update/', views.MyServiceRequestUpdateView.as_view(), name='my-request-update'),
    path('requests/my-requests/<int:pk>/cancel/', views.ServiceRequestCancelView.as_view(), name='request-cancel'),
    path('requests/my-statistics/', views.my_requests_statistics, name='my-requests-statistics'),
    
    # Admin URLs
    path('admin/requests/', views.AdminServiceRequestListView.as_view(), name='admin-requests'),
    path('admin/requests/<int:pk>/', views.AdminServiceRequestRetrieveView.as_view(), name='admin-request-detail'),
    path('admin/requests/<int:pk>/update/', views.AdminServiceRequestUpdateView.as_view(), name='admin-request-update'),
    path('admin/my-services/', views.MyServicesListView.as_view(), name='my-services'),
]