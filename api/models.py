import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50)
    breed = models.CharField(max_length=50, blank=True, null=True)
    birth_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.owner.first_name} {self.owner.last_name})"
    
    def delete(self, *args, **kwargs):
        
        #1. Check if the pet is active before allowing deletion
        if self.status == 'active':
            raise ValidationError("Cannot delete an active pet. Please change the status to 'inactive' before deleting.")
        
       #2. Check if the pet is active medical records in the database before allowing deletion
        active_medical_records = self.medical_records.filter(is_deleted=False).exists()
        if active_medical_records:
            raise ValidationError("Cannot delete a pet with active medical records. Please delete or mark the medical records as deleted before deleting the pet.") 
        
        #3. If the pet is inactive and has no active medical records, proceed with deletion
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pet = models.ForeignKey(Pet, on_delete=models.PROTECT, related_name='medical_records')
    type_record = models.CharField(max_length=20, choices=TYPES)
    description = models.TextField()
    application_date = models.DateTimeField(default=timezone.now)
    booster_date = models.DateTimeField(blank=True, null=True)
    
    is_deleted = models.BooleanField(default=False)
    elimination_date = models.DateTimeField(blank=True, null=True)
    
    def soft_delete(self):
        self.is_deleted = True
        self.elimination_date = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.type_record} for {self.pet.name} ({self.pet.owner.first_name} {self.pet.owner.last_name} ({self.pet.application_date.strftime('%Y-%m-%d')}))"