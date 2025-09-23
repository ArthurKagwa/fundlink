from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NGOViewSet

router = DefaultRouter()
router.register(r'ngos', NGOViewSet)

urlpatterns = [
    path('', include(router.urls)),
]