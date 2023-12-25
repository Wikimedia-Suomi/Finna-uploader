from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FinnaImageViewSet

router = DefaultRouter()
router.register(r'finnaimage', FinnaImageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
