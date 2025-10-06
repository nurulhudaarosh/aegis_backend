from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    EmergencyAlert, IncidentUpdate, ResourceCategory, ExternalLink, QuizOption, QuizQuestion,
    LearningResource, SafetyCheckIn, SafetyCheckSettings, UserProgress, UserQuizAttempt,EmergencyContact,
    IncidentReport, IncidentMedia, VideoEvidence,

)

User = get_user_model()

class EmergencyContactSerializer(serializers.ModelSerializer):
    photo = serializers.SerializerMethodField()
    
    class Meta:
        model = EmergencyContact
        fields = ('id', 'name', 'phone', 'email', 'relationship', 'is_emergency_contact', 
                 'is_primary', 'photo', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_photo(self, obj):
        # Return emoji based on relationship
        relationship_emojis = {
            'family': '👨‍👩‍👧‍👦',
            'friend': '👥',
            'colleague': '💼',
            'neighbor': '🏠',
            'emergency_service': '🚨',
            'other': '👤'
        }
        return relationship_emojis.get(obj.relationship, '👤')
    
    def validate_phone(self, value):
        # Basic phone validation
        if not value.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits and valid symbols.")
        return value

class EmergencyContactCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ('name', 'phone', 'email', 'relationship', 'is_emergency_contact', 'is_primary')
    
    def validate_phone(self, value):
        if not value.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits and valid symbols.")
        return value

class UserWithContactsSerializer(serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    emergency_contacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'emergency_contacts', 'emergency_contacts_count')
    
    def get_emergency_contacts_count(self, obj):
        return obj.emergency_contacts.count()

class PhoneLookupSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    
    def validate_phone(self, value):
        if not value.replace('+', '').replace(' ', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Invalid phone number format.")
        return value

class UserLookupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('name', 'email', 'phone')




# learn

class ResourceCategorySerializer(serializers.ModelSerializer):
    resource_count = serializers.SerializerMethodField()

    class Meta:
        model = ResourceCategory
        fields = ('id', 'name', 'description', 'icon', 'order', 'resource_count')

    def get_resource_count(self, obj):
        return obj.resources.filter(is_published=True).count()


class ExternalLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalLink
        fields = ('id', 'title', 'url', 'description', 'order')


class QuizOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizOption
        fields = ('id', 'text','is_correct','order')


class QuizQuestionSerializer(serializers.ModelSerializer):
    options = QuizOptionSerializer(many=True, read_only=True)

    class Meta:
        model = QuizQuestion
        fields = ('id', 'question', 'explanation', 'options', 'order')


class LearningResourceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    external_links = ExternalLinkSerializer(many=True, read_only=True)
    quiz_questions = QuizQuestionSerializer(many=True, read_only=True)
    user_progress = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = LearningResource
        fields = (
            'id', 'title', 'description', 'content', 'resource_type', 'difficulty',
            'duration', 'icon', 'category', 'category_name', 'video_url', 'thumbnail',
            'external_links', 'quiz_questions', 'user_progress', 'is_bookmarked',
            'created_at', 'updated_at', 'is_published'
        )

    def get_user_progress(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = UserProgress.objects.filter(
                user=request.user, resource=obj
            ).first()
            if progress:
                return {
                    'completed': progress.completed,
                    'progress_percentage': progress.progress_percentage,
                    'bookmarked': progress.bookmarked,
                    'time_spent': progress.time_spent,
                }
        return None

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserProgress.objects.filter(
                user=request.user, resource=obj, bookmarked=True
            ).exists()
        return False


class UserProgressSerializer(serializers.ModelSerializer):
    resource_title = serializers.CharField(source='resource.title', read_only=True)
    resource_type = serializers.CharField(source='resource.resource_type', read_only=True)

    class Meta:
        model = UserProgress
        fields = (
            'id', 'resource', 'resource_title', 'resource_type', 'completed',
            'progress_percentage', 'bookmarked', 'time_spent', 'last_accessed'
        )


class QuizAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    option_id = serializers.IntegerField()


class QuizSubmissionSerializer(serializers.Serializer):
    answers = QuizAnswerSerializer(many=True)
    time_spent = serializers.IntegerField(min_value=0)


class UserQuizAttemptSerializer(serializers.ModelSerializer):
    resource_title = serializers.CharField(source='resource.title', read_only=True)

    class Meta:
        model = UserQuizAttempt
        fields = (
            'id', 'resource', 'resource_title', 'score', 'total_questions',
            'correct_answers', 'completed_at'
        )



# report

class IncidentMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentMedia
        fields = ('id', 'media_type', 'file', 'caption', 'created_at')
        read_only_fields = ('id', 'created_at')

class IncidentUpdateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model = IncidentUpdate
        fields = ('id', 'status', 'message', 'created_by_name', 'created_at')
        read_only_fields = ('id', 'created_at')

    def create(self, validated_data):
        request = self.context.get('request')
        incident = self.context.get('incident') 
        print(request,incident)
        if not incident:
            raise serializers.ValidationError("Incident context missing.")
        validated_data['incident'] = incident

        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        else:
            raise serializers.ValidationError("Authenticated user required to create update.")
        
        return super().create(validated_data)


class IncidentReportSerializer(serializers.ModelSerializer):
    media = IncidentMediaSerializer(many=True, read_only=True)
    updates = IncidentUpdateSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = IncidentReport
        fields = (
            'id', 'incident_type', 'title', 'description', 'location',
            'incident_date', 'latitude', 'longitude', 'is_anonymous',
            'status', 'priority', 'media', 'updates', 'user_name',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'status', 'priority', 'created_at', 'updated_at')

class IncidentReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentReport
        fields = (
            'incident_type', 'title', 'description', 'location',
            'incident_date', 'latitude', 'longitude', 'is_anonymous'
        )

    def validate_incident_date(self, value):
        from django.utils import timezone
        if value > timezone.now():
            raise serializers.ValidationError("Incident date cannot be in the future.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class MediaUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentMedia
        fields = ('media_type', 'file', 'caption', 'incident')
        extra_kwargs = {
            'incident': {'required': False}
        }



# safety check

class SafetyCheckSettingsSerializer(serializers.ModelSerializer):
    frequency_display = serializers.CharField(source='get_check_in_frequency_display', read_only=True)

    class Meta:
        model = SafetyCheckSettings
        fields = (
            'id', 'is_enabled', 'check_in_frequency', 'frequency_display',
            'notify_emergency_contacts', 'share_location', 'created_at', 'updated_at'
        )

class SafetyCheckInSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = SafetyCheckIn
        fields = (
            'id', 'user', 'user_email', 'status', 'scheduled_at', 'responded_at',
            'location_lat', 'location_lng', 'notes', 'is_overdue', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

class EmergencyAlertSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)

    class Meta:
        model = EmergencyAlert
        fields = (
            'id', 'user', 'user_email', 'alert_type', 'alert_type_display',
            'message', 'location_lat', 'location_lng', 'sent_to_contacts',
            'sent_to_authorities', 'created_at'
        )
        read_only_fields = ('id', 'user', 'created_at')

class SafetyStatisticsSerializer(serializers.Serializer):
    total_check_ins = serializers.IntegerField()
    successful_check_ins = serializers.IntegerField()
    missed_check_ins = serializers.IntegerField()
    emergency_alerts = serializers.IntegerField()
    response_rate = serializers.FloatField()
    last_check_in = serializers.DateTimeField(allow_null=True)
    next_check_in = serializers.DateTimeField(allow_null=True)

class ManualCheckInSerializer(serializers.Serializer):
    location_lat = serializers.FloatField(required=False, allow_null=True)
    location_lng = serializers.FloatField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)

class TestAlertSerializer(serializers.Serializer):
    message = serializers.CharField(default="This is a test emergency alert")



# silent capture or evidence

class VideoEvidenceSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    file_size_display = serializers.CharField(source='get_file_size_display', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)
    video_url = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = VideoEvidence
        fields = (
            'id', 'user', 'user_email', 'title', 'video_file', 'video_url',
            'location_lat', 'location_lng', 'location_address', 'recorded_at',
            'is_anonymous', 'duration_seconds', 'duration_display',
            'file_size', 'file_size_display', 'status', 'type',
            'created_at', 'updated_at', 'can_edit'
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at', 'file_size', 'status')

    def get_video_url(self, obj):
        if obj.video_file:
            return obj.video_file.url
        return None

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request:
            return obj.user_can_modify(request.user)
        return False

class VideoEvidenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoEvidence
        fields = (
            'title', 'location_lat', 'location_lng', 'location_address',
            'recorded_at', 'is_anonymous', 'duration_seconds', 'type'
        )

class VideoEvidenceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoEvidence
        fields = (
            'title', 'location_lat', 'location_lng', 'location_address',
            'recorded_at', 'is_anonymous', 'duration_seconds', 'type'
        )
        read_only_fields = ('status',)

    def validate_type(self, value):
        if value not in [choice[0] for choice in VideoEvidence.EVIDENCE_TYPE]:
            raise serializers.ValidationError("Invalid evidence type")
        return value

class VideoEvidenceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoEvidence
        fields = ('status',)
        
    def validate_status(self, value):
        if value not in [choice[0] for choice in VideoEvidence.STATUS_CHOICES]:
            raise serializers.ValidationError("Invalid status")
        return value

class VideoUploadSerializer(serializers.Serializer):
    video_file = serializers.FileField(
        max_length=100 * 1024 * 1024,
        allow_empty_file=False
    )
    media_type = serializers.CharField(default='video')

    def validate_video_file(self, value):
        allowed_extensions = ['mp4', 'mov', 'avi', 'mkv', 'webm']
        file_extension = value.name.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported video format. Allowed formats: {', '.join(allowed_extensions)}"
            )

        if not value.content_type.startswith('video/'):
            raise serializers.ValidationError("Uploaded file must be a video")

        return value