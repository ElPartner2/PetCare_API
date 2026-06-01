from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
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
            return Response({"detail": "Pet deleted successfully from the database."}, status=status.HTTP_200_OK)
        except DjangoValidationError as e:
            return Response({'detail': e.message}, status=status.HTTP_400_BAD_REQUEST)

class MedicalRecordViewSet(viewsets.ModelViewSet):
    
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return MedicalRecord.objects.filter(pet__owner=self.request.user, is_deleted=False)
    
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
        return Response({"detail": "Medical record successfully archived (soft deleted)"}, status=status.HTTP_200_OK)
    