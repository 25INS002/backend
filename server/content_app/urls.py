from django.urls import path
from .views import ContentListView, ContentReadView, ContentUpdateView

urlpatterns = [
    path('list/', ContentListView.as_view(), name='content-list'),
    path('read/', ContentReadView.as_view(), name='content-read'),
    path('update/', ContentUpdateView.as_view(), name='content-update'),
]
