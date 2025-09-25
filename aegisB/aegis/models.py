from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import uuid
import os

User = get_user_model()


def incident_media_upload_path(instance, filename):
    """Generate upload path for incident media files"""
    date_str = timezone.now().strftime('%Y/%m/%d')
    return f'incident_media/{date_str}/{instance.incident.id}/{filename}'

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
            

class ResourceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='📚')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Resource Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class LearningResource(models.Model):
    RESOURCE_TYPES = [
        ('article', 'Article'),
        ('video', 'Video'),
        ('quiz', 'Quiz'),
        ('guide', 'Guide'),
        ('tutorial', 'Tutorial'),
    ]

    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    content = models.TextField(help_text="Markdown-formatted content")
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS, default='beginner')
    duration = models.CharField(max_length=50, help_text="e.g., '5 min read', '10 min video'")
    icon = models.CharField(max_length=50, default='📄')
    category = models.ForeignKey(ResourceCategory, on_delete=models.SET_NULL, null=True, related_name='resources')
    video_url = models.URLField(blank=True, null=True)
    thumbnail = models.ImageField(upload_to='resource_thumbnails/', blank=True, null=True)
    is_published = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    related_resources = models.ManyToManyField('self', blank=True, symmetrical=False)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.title

    def clean(self):
        if self.resource_type == 'video' and not self.video_url:
            raise ValidationError('Video resources must have a video URL.')


class ExternalLink(models.Model):
    resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE, related_name='external_links')
    title = models.CharField(max_length=200)
    url = models.URLField()
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return f"{self.title} - {self.resource.title}"


class QuizQuestion(models.Model):
    resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE, related_name='quiz_questions')
    question = models.TextField()
    explanation = models.TextField(help_text="Explanation shown after answering")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q: {self.question[:50]}..."


class QuizOption(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.text[:50]}... ({'✓' if self.is_correct else '✗'})"


class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_progress')
    resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    progress_percentage = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(auto_now=True)
    bookmarked = models.BooleanField(default=False)
    time_spent = models.IntegerField(default=0)  # in seconds

    class Meta:
        unique_together = ['user', 'resource']
        verbose_name_plural = "User Progress"

    def __str__(self):
        return f"{self.user.email} - {self.resource.title}"


class UserQuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE)
    total_questions = models.IntegerField()
    correct_answers = models.IntegerField()
    completed_at = models.DateTimeField(auto_now_add=True)
    answers = models.JSONField()  

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user.email} - {self.resource.title} ({self.correct_answers}/{self.total_questions})"

    @property
    def score(self):
        return (self.correct_answers / self.total_questions) * 100 if self.total_questions else 0



# report 
class IncidentReport(models.Model):
    INCIDENT_TYPES = [
        ('harassment', 'Harassment'),
        ('robbery', 'Robbery'),
        ('assault', 'Assault'),
        ('stalking', 'Stalking'),
        ('theft', 'Theft'),
        ('vandalism', 'Vandalism'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incident_reports')
    incident_type = models.CharField(max_length=20, choices=INCIDENT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.TextField(blank=True, null=True)
    incident_date = models.DateTimeField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_anonymous = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_incident_type_display()} - {self.title}"

    def clean(self):
        if self.incident_date and self.incident_date > timezone.now():
            raise ValidationError('Incident date cannot be in the future.')

class IncidentMedia(models.Model):
    MEDIA_TYPES = [
        ('photo', 'Photo'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]

    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    file = models.FileField(upload_to=incident_media_upload_path)
    caption = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_media_type_display()} - {self.incident.title}"

class IncidentUpdate(models.Model):
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name='updates')
    status = models.CharField(max_length=20, choices=IncidentReport.STATUS_CHOICES)
    message = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Update for {self.incident.title}"