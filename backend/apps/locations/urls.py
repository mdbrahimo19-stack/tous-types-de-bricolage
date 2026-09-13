from rest_framework.routers import DefaultRouter

from .views import AddressViewSet, CommuneViewSet, WilayaViewSet

app_name = "locations"

router = DefaultRouter()
router.register("wilayas", WilayaViewSet, basename="wilaya")
router.register("communes", CommuneViewSet, basename="commune")
router.register("addresses", AddressViewSet, basename="address")

urlpatterns = router.urls
