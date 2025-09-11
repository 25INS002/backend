from django.urls import path
from .views import (
    FeedbackCreateView,
    ModuleFeedbackListView,
    FeedbackUpdateView,
    FeedbackDeleteView,
)

urlpatterns = [
    path("create/", FeedbackCreateView.as_view(), name="feedback-create"),
    path("module/<int:module_id>/", ModuleFeedbackListView.as_view(), name="feedback-list"),
    path("update/<int:pk>/", FeedbackUpdateView.as_view(), name="feedback-update"),
    path("delete/<int:pk>/", FeedbackDeleteView.as_view(), name="feedback-delete"),
]
