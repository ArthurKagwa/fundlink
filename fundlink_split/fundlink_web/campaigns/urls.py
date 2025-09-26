from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CampaignViewSet, ImpactPostViewSet

router = DefaultRouter()
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'impact-posts', ImpactPostViewSet, basename='impactpost')

urlpatterns = [
    path('', include(router.urls)),
]