from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DonationViewSet, donor_history

router = DefaultRouter()
router.register(r'donations', DonationViewSet, basename='donation')

urlpatterns = [
    path('', include(router.urls)),
    path('donor-history/', donor_history, name='donor-history'),
]