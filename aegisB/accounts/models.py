from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.exceptions import ValidationError
from .managers import CustomUserManager

# Custom user model
class CustomUser(AbstractUser):
    USER_TYPES = [
        ('user', 'User'),
        ('agent', 'Agent'),
        ('controller', 'Controller'),
        ('admin', 'Admin'),
    ]

    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    ID_TYPE_CHOICES = [
        ('nid', 'National ID (NID)'),
        ('birth', 'Birth Certificate'),
    ]

    # Remove username and first/last name
    username = None
    first_name = None
    last_name = None

    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='user')
    agent_id = models.CharField(max_length=20, blank=True, null=True, unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    phone = models.CharField(max_length=20, blank=True)
    id_type = models.CharField(max_length=10, choices=ID_TYPE_CHOICES, default='nid')
    id_number = models.CharField(max_length=50, blank=True)
    dob = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=5, blank=True,null=True)
    address = models.TextField(blank=True,null=True)
    emergency_medical_note = models.TextField(blank=True,null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = [] 

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    @property
    def name(self):
        return self.full_name

    def clean(self):

        if self.user_type == 'agent' and not self.agent_id:
            raise ValidationError({'agent_id': 'Agent ID is required for agent users.'})

        if self.user_type == 'user' and self.agent_id:
            raise ValidationError({'agent_id': 'Agent ID should not be provided for regular users.'})
