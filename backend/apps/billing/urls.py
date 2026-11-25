from django.urls import path

from .views import CardPaymentSyncView, CardPaymentView, PaymentsView, PointsView, card_done, chargily_webhook

app_name = "billing"

urlpatterns = [
    path("provider/points/", PointsView.as_view(), name="points"),
    path("provider/payments/", PaymentsView.as_view(), name="payments"),
    # paiement par carte Edahabia / CIB (Chargily Pay)
    path("provider/payments/card/", CardPaymentView.as_view(), name="card-payment"),
    path("provider/payments/<int:pk>/sync/", CardPaymentSyncView.as_view(), name="card-sync"),
    path("billing/chargily/webhook/", chargily_webhook, name="chargily-webhook"),
    path("billing/paiement-termine/", card_done, name="card-done"),
]
