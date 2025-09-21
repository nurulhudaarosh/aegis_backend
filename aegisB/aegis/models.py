from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class EmergencyContact(models.Model):
    RELATIONSHIP_CHOICES = [
        ('family', 'Family'),
        ('friend', 'Friend'),
        ('colleague', 'Colleague'),
        ('neighbor', 'Neighbor'),
        ('emergency_service', 'Emergency Service'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='emergency_contacts')
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='friend')
    is_emergency_contact = models.BooleanField(default=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'phone']
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return f"{self.name} ({self.phone}) - {self.user.email}"

    def clean(self):
        # Ensure only one primary contact per user
        if self.is_primary:
            primary_exists = EmergencyContact.objects.filter(
                user=self.user, 
                is_primary=True
            ).exclude(pk=self.pk).exists()
            if primary_exists:
                raise ValidationError('User can only have one primary emergency contact.')