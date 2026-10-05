from django.urls import path

from .views import DraftRequestView, PriceEstimateView, SupportView

app_name = "ai"

urlpatterns = [
    path("draft-request/", DraftRequestView.as_view(), name="draft-request"),
    path("price-estimate/", PriceEstimateView.as_view(), name="price-estimate"),
    path("support/", SupportView.as_view(), name="support"),
]
