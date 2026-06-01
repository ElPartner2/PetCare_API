from rest_framework import serializers
from .models import User, Pet, MedicalRecord
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone']
        read_only_fields = ['id']
        
class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = ['id', 'pet', 'type_record', 'application_date', 'description', 'booster_date']
        read_only_fields = ['id', 'application_date']
        
    def validate_booster_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Booster date cannot be before the application date.")
        return value
    
class PetSerializer(serializers.ModelSerializer):
    medical_records = MedicalRecordSerializer(many=True, read_only=True)
    
    class Meta:
        model = Pet
        fields = ['id', 'owner', 'name', 'species', 'breed', 'birth_date', 'status', 'created_date', 'medical_records']
        read_only_fields = ['id', 'owner', 'created_date', 'medical_records']
        
    def validate_birth_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Birth date cannot be in the future.")
        return value