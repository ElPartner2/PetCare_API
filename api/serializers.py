from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Pet, MedicalRecord
from django.utils import timezone


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'username'

    def validate(self, attrs):
        username = attrs.get('username') or attrs.get('email')
        password = attrs.get('password')

        if not username:
            raise serializers.ValidationError({'username': ['This field is required.']})
        if not password:
            raise serializers.ValidationError({'password': ['This field is required.']})

        attrs = {'username': username, 'password': password}
        return super().validate(attrs)


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
        
    def validate(self, attrs):
        attrs = super().validate(attrs)
        application_date = attrs.get('application_date')
        if application_date is None:
            application_date = (
                self.instance.application_date if self.instance else timezone.now()
            )

        booster_date = attrs.get('booster_date')
        if booster_date is None and self.instance and 'booster_date' not in attrs:
            booster_date = self.instance.booster_date

        if booster_date and booster_date < application_date:
            raise serializers.ValidationError({
                'booster_date': 'Booster date cannot be before the application date.'
            })
        return attrs
    
class PetSerializer(serializers.ModelSerializer):
    medical_records = serializers.SerializerMethodField()
    
    class Meta:
        model = Pet
        fields = ['id', 'owner', 'name', 'species', 'breed', 'birth_date', 'status', 'created_date', 'medical_records']
        read_only_fields = ['id', 'owner', 'created_date', 'medical_records']
        
    def validate_birth_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError("Birth date cannot be in the future.")
        return value

    def get_medical_records(self, obj):
        records = obj.medical_records.filter(is_deleted=False)
        return MedicalRecordSerializer(records, many=True, context=self.context).data
