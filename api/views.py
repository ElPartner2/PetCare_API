from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models.deletion import ProtectedError
from .models import Pet, MedicalRecord
from .serializers import PetSerializer, MedicalRecordSerializer

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
        pet = serializer.validated_data.get('pet')
        if pet.owner != self.request.user:
            raise PermissionDenied("You do not have permission to add a medical record for this pet.")
        serializer.save()
    
    def perform_update(self, serializer):
        pet = serializer.validated_data.get('pet')
        if pet and pet.owner != self.request.user:
            raise PermissionDenied("You do not have permission to update a medical record for this pet.")
        serializer.save()
        
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
