from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicalRecordViewSet, PetViewSet, UserRegistrationView

router = DefaultRouter()

router.register(r'pets', PetViewSet, basename='pet')
router.register(r'medical-records', MedicalRecordViewSet, basename='medicalrecord')

urlpatterns = [
    path('users/register/', UserRegistrationView.as_view(), name='user-register'),
    path('', include(router.urls)),
]
