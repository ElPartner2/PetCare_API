from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User, Pet, MedicalRecord
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'username'

    def validate(self, attrs):
        username = attrs.get('username') or attrs.get('email')
        password = attrs.get('password')

        if not username:
            raise serializers.ValidationError({
                'username': ['This field is required.']
            })

        if not password:
            raise serializers.ValidationError({
                'password': ['This field is required.']
            })

        attrs = {
            'username': username,
            'password': password
        }
        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone'
        ]
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False
    )

    password_confirm = serializers.CharField(
        write_only=True,
        trim_whitespace=False
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'password',
            'password_confirm',
        ]

        read_only_fields = ['id']

        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'phone': {'required': True},
        }

    def validate_email(self, value):
        normalized_email = User.objects.normalize_email(value)

        if User.objects.filter(
            email__iexact=normalized_email
        ).exists():
            raise serializers.ValidationError(
                'A user with this email already exists.'
            )

        return normalized_email

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Passwords do not match.'
            })

        candidate = User(
            username=attrs.get('username'),
            email=attrs.get('email'),
            first_name=attrs.get('first_name'),
            last_name=attrs.get('last_name'),
            phone=attrs.get('phone'),
        )

        try:
            validate_password(
                attrs['password'],
                user=candidate
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({
                'password': list(exc.messages)
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')

        return User.objects.create_user(
            password=password,
            **validated_data
        )


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = [
            'id',
            'pet',
            'type_record',
            'application_date',
            'description',
            'booster_date'
        ]

        read_only_fields = [
            'id',
            'application_date'
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        application_date = attrs.get('application_date')

        if application_date is None:
            application_date = (
                self.instance.application_date
                if self.instance
                else timezone.now()
            )

        booster_date = attrs.get('booster_date')

        if (
            booster_date is None
            and self.instance
            and 'booster_date' not in attrs
        ):
            booster_date = self.instance.booster_date

        if booster_date and booster_date < application_date:
            raise serializers.ValidationError({
                'booster_date':
                    'Booster date cannot be before the application date.'
            })

        return attrs


class PetSerializer(serializers.ModelSerializer):
    medical_records = serializers.SerializerMethodField()

    class Meta:
        model = Pet

        fields = [
            'id',
            'owner',
            'name',
            'species',
            'breed',
            'birth_date',
            'sex',
            'weight',
            'color',
            'distinctive_marks',
            'observations',
            'allergies',
            'medical_conditions',
            'current_medications',
            'status',
            'created_date',
            'medical_records',
        ]

        read_only_fields = [
            'id',
            'owner',
            'created_date',
            'medical_records'
        ]

    def validate_birth_date(self, value):
        if value and value > timezone.localdate():
            raise serializers.ValidationError(
                "Birth date cannot be in the future."
            )

        return value

    def get_medical_records(self, obj):
        records = obj.medical_records.filter(
            is_deleted=False
        )

        return MedicalRecordSerializer(
            records,
            many=True,
            context=self.context
        ).data
