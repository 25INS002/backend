from django.urls import path
from .views import (
    EventCreateView, EventListView, EventRetrieveView,
    EventUpdateView, EventDeleteView, AddParticipantView,
    ActiveEventsView, FinishedEventsView, ScheduledEventsView,
    UserEventsView,CheckParticipationView,
)

urlpatterns = [
    path("create/", EventCreateView.as_view(), name="event-create"),
    path("list/", EventListView.as_view(), name="event-list"),
    path("retrieve/<int:pk>/", EventRetrieveView.as_view(), name="event-retrieve"),
    path("update/<int:pk>/", EventUpdateView.as_view(), name="event-update"),
    path("delete/<int:pk>/", EventDeleteView.as_view(), name="event-delete"),
    path("add-participant/<int:pk>/", AddParticipantView.as_view(), name="event-add-participant"),
    path("events/active/", ActiveEventsView.as_view(), name="event-active"),
    path("events/finished/", FinishedEventsView.as_view(), name="event-finished"),
    path("events/scheduled/", ScheduledEventsView.as_view(), name="event-scheduled"),
    path("events/my/", UserEventsView.as_view(), name="user-events"),
    path("events/<int:pk>/participants/me/", CheckParticipationView.as_view(), name="check-participation"),
]
