from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DonationViewSet,
    donor_history,
    create_donation_intent,
    list_donation_intents,
    confirm_donation,
)

router = DefaultRouter()
router.register(r'donations', DonationViewSet, basename='donation')

urlpatterns = [
    path('donations/intents/', create_donation_intent, name='donation-intent-create'),
    path('donations/intents/list/', list_donation_intents, name='donation-intent-list'),
    path('donations/confirm/', confirm_donation, name='donation-confirm'),
    path('donor-history/', donor_history, name='donor-history'),
    path('', include(router.urls)),
]
