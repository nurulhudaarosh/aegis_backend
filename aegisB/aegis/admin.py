from django.contrib import admin
from . import models

admin.site.register(models.EmergencyContact)


class ExternalLinkInline(admin.TabularInline):
    model = models.ExternalLink
    extra = 1


class QuizOptionInline(admin.TabularInline):
    model = models.QuizOption
    extra = 4


class QuizQuestionInline(admin.TabularInline):
    model = models.QuizQuestion
    extra = 1


@admin.register(models.ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    ordering = ('order', 'name')


@admin.register(models.LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'resource_type', 'difficulty', 'category',
        'is_published', 'order', 'created_at'
    )
    list_filter = ('resource_type', 'difficulty', 'is_published', 'category')
    search_fields = ('title', 'description', 'content')
    ordering = ('order', 'created_at')
    inlines = [ExternalLinkInline, QuizQuestionInline]
    filter_horizontal = ('related_resources',)


@admin.register(models.QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_preview', 'resource', 'order')
    list_filter = ('resource',)
    search_fields = ('question',)
    ordering = ('order',)
    inlines = [QuizOptionInline]

    def question_preview(self, obj):
        return obj.question[:75] + ("..." if len(obj.question) > 75 else "")
    question_preview.short_description = "Question"


@admin.register(models.QuizOption)
class QuizOptionAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'question', 'is_correct', 'order')
    list_filter = ('is_correct', 'question')
    search_fields = ('text',)
    ordering = ('order',)

    def text_preview(self, obj):
        return obj.text[:75] + ("..." if len(obj.text) > 75 else "")
    text_preview.short_description = "Option Text"


@admin.register(models.ExternalLink)
class ExternalLinkAdmin(admin.ModelAdmin):
    list_display = ('title', 'resource', 'url', 'order')
    search_fields = ('title', 'url')
    ordering = ('order', 'title')


@admin.register(models.UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'resource', 'completed', 'progress_percentage',
        'bookmarked', 'time_spent', 'last_accessed'
    )
    list_filter = ('completed', 'bookmarked')
    search_fields = ('user__email', 'resource__title')
    ordering = ('-last_accessed',)


@admin.register(models.UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'resource', 'score',
        'correct_answers', 'total_questions', 'completed_at'
    )
    list_filter = ('completed_at', 'resource')
    search_fields = ('user__email', 'resource__title')
    ordering = ('-completed_at',)


admin.site.register(models.IncidentReport)
admin.site.register(models.IncidentUpdate)
admin.site.register(models.IncidentMedia)



@admin.register(models.SafetyCheckSettings)
class SafetyCheckSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_enabled', 'check_in_frequency', 'notify_emergency_contacts', 'share_location', 'updated_at')
    list_filter = ('is_enabled', 'notify_emergency_contacts', 'share_location', 'check_in_frequency')
    search_fields = ('user__email', 'user__name')
    list_editable = ('is_enabled', 'notify_emergency_contacts', 'share_location')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(models.SafetyCheckIn)
class SafetyCheckInAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'scheduled_at', 'responded_at', 'is_overdue', 'created_at')
    list_filter = ('status', 'scheduled_at', 'created_at')
    search_fields = ('user__email', 'user__name', 'notes')
    readonly_fields = ('created_at', 'is_overdue')
    date_hierarchy = 'scheduled_at'

@admin.register(models.EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'alert_type', 'sent_to_contacts', 'sent_to_authorities', 'created_at')
    list_filter = ('alert_type', 'sent_to_contacts', 'sent_to_authorities', 'created_at')
    search_fields = ('user__email', 'user__name', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


# silent capture
@admin.register(models.VideoEvidence)
class VideoEvidenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'recorded_at', 'duration_display', 'file_size_display', 'is_anonymous')
    list_filter = ('is_anonymous', 'recorded_at', 'created_at')
    search_fields = ('title', 'user__email', 'location_address')
    readonly_fields = ('created_at', 'updated_at', 'file_size')
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'video_file', 'is_anonymous')
        }),
        ('Location', {
            'fields': ('location_lat', 'location_lng', 'location_address')
        }),
        ('Recording Details', {
            'fields': ('recorded_at', 'duration_seconds', 'file_size')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def duration_display(self, obj):
        return obj.get_duration_display()
    duration_display.short_description = 'Duration'

    def file_size_display(self, obj):
        return obj.get_file_size_display()
    file_size_display.short_description = 'File Size'