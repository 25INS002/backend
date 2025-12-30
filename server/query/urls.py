from django.urls import path
from .views import ContactMessageCreateView, ContactMessageAdminListView, ContactMessageAdminUpdateView
# urls.py
urlpatterns = [
    # Public
    path("contact/submit/", ContactMessageCreateView.as_view(), name="contact-submit"),

    # Admin
    path("admin/contact/", ContactMessageAdminListView.as_view(), name="admin-contact-list"),
    path("admin/contact/<int:pk>/", ContactMessageAdminUpdateView.as_view(), name="admin-contact-detail"),
]
