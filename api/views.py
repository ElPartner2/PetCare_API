from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import CreateAPIView
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from .models import Pet, MedicalRecord
from .serializers import (
    MedicalRecordSerializer,
    PetSerializer,
    UserRegistrationSerializer,
)


class UserRegistrationView(CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

class PetViewSet(viewsets.ModelViewSet):

    serializer_class = PetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Pet.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except DjangoValidationError as e:
            return Response({'detail': e.message}, status=status.HTTP_409_CONFLICT)
        except ProtectedError:
            return Response(
                {'detail': 'Cannot delete a pet with associated medical records.'},
                status=status.HTTP_409_CONFLICT,
            )

class MedicalRecordViewSet(viewsets.ModelViewSet):
    
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = MedicalRecord.objects.filter(
            pet__owner=self.request.user,
            is_deleted=False,
        )
        pet_id = self.request.query_params.get('pet')
        if pet_id:
            try:
                pet_id = serializers.UUIDField().run_validation(pet_id)
            except serializers.ValidationError:
                raise serializers.ValidationError({'pet': 'Must be a valid UUID.'})
            queryset = queryset.filter(pet_id=pet_id)
        return queryset
    
    def perform_create(self, serializer):
        pet = serializer.validated_data['pet']
        if pet.owner_id != self.request.user.id:
            raise PermissionDenied(
                'You cannot add a medical record to another user’s pet.'
            )
        serializer.save()
    
    def perform_update(self, serializer):
        pet = serializer.validated_data.get('pet')
        if pet and pet.owner_id != self.request.user.id:
            raise PermissionDenied(
                'You cannot reassign a medical record to another user’s pet.'
            )
        serializer.save()
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
