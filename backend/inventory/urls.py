

from django.urls import path, include
from rest_framework import routers
from .views import (
    InventoryCategoryViewSet,
    InventoryItemViewSet,
    InventoryTransactionViewSet,
    InventoryReservationViewSet,
    ServiceTypeInventoryRequirementViewSet,
)

router = routers.DefaultRouter()
router.register(r'categories', InventoryCategoryViewSet)
router.register(r'items', InventoryItemViewSet)
router.register(r'transactions', InventoryTransactionViewSet)
router.register(r'reservations', InventoryReservationViewSet)
router.register(r'service-type-requirements', ServiceTypeInventoryRequirementViewSet)

urlpatterns = [
    path('', include(router.urls)),
]


