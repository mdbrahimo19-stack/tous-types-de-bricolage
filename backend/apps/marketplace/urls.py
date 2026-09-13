from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ConversationViewSet,
    DeviceRegisterView,
    MessageFlagView,
    MissionViewSet,
    NotificationViewSet,
    ProviderCategoryViewSet,
    ProviderProfileView,
    PublicProviderViewSet,
    QuoteViewSet,
    RequestFeedViewSet,
    ReviewReplyView,
    ServiceRequestViewSet,
)

app_name = "marketplace"

router = DefaultRouter()
router.register("requests", ServiceRequestViewSet, basename="request")
router.register("feed", RequestFeedViewSet, basename="feed")
router.register("quotes", QuoteViewSet, basename="quote")
router.register("missions", MissionViewSet, basename="mission")
router.register("provider/categories", ProviderCategoryViewSet, basename="provider-category")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("providers", PublicProviderViewSet, basename="provider-public")

urlpatterns = [
    path("provider/me/", ProviderProfileView.as_view(), name="provider-me"),
    path("messages/<int:pk>/flag/", MessageFlagView.as_view(), name="message-flag"),
    path("reviews/<int:pk>/reply/", ReviewReplyView.as_view(), name="review-reply"),
    path("devices/", DeviceRegisterView.as_view(), name="device-register"),
    *router.urls,
]
