from django.urls import path

from .views import PaymentsView, PointsView

app_name = "billing"

urlpatterns = [
    path("provider/points/", PointsView.as_view(), name="points"),
    path("provider/payments/", PaymentsView.as_view(), name="payments"),
]
