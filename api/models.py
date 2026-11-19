import uuid

from decimal import Decimal
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username or self.email


class Pet(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='pets'
    )

    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50)
    breed = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    birth_date = models.DateField()

    # Datos adicionales para el carnet digital
    sex = models.CharField(
        max_length=10,
        choices=SEX_CHOICES,
        blank=True,
        default=''
    )

    weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(Decimal('0.01'))
        ]
    )

    color = models.CharField(
        max_length=60,
        blank=True,
        default=''
    )

    distinctive_marks = models.TextField(
        blank=True,
        default=''
    )

    observations = models.TextField(
        blank=True,
        default=''
    )

    allergies = models.TextField(
        blank=True,
        default=''
    )

    medical_conditions = models.TextField(
        blank=True,
        default=''
    )

    current_medications = models.TextField(
        blank=True,
        default=''
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.name} "
            f"({self.owner.first_name} {self.owner.last_name})"
        )

    def delete(self, *args, **kwargs):
        if self.status == 'active':
            raise ValidationError(
                "Cannot delete an active pet. "
                "Please change the status to 'inactive' "
                "before deleting."
            )

        if self.medical_records.exists():
            raise ValidationError(
                "Cannot delete a pet with associated medical records."
            )

        super().delete(*args, **kwargs)


class MedicalRecord(models.Model):
    TYPES = [
        ('vaccination', 'Vaccination'),
        ('checkup', 'Checkup'),
        ('surgery', 'Surgery'),
        ('deworming', 'Deworming'),
        ('sterilization', 'Sterilization'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    pet = models.ForeignKey(
        Pet,
        on_delete=models.PROTECT,
        related_name='medical_records'
    )

    type_record = models.CharField(
        max_length=20,
        choices=TYPES
    )

    description = models.TextField()

    application_date = models.DateTimeField(
        default=timezone.now
    )

    booster_date = models.DateTimeField(
        blank=True,
        null=True
    )

    is_deleted = models.BooleanField(default=False)

    elimination_date = models.DateTimeField(
        blank=True,
        null=True
    )

    def soft_delete(self):
        self.is_deleted = True
        self.elimination_date = timezone.now()
        self.save()

    def __str__(self):
        return (
            f"{self.type_record} for {self.pet.name} "
            f"({self.application_date.strftime('%Y-%m-%d')})"
        )
