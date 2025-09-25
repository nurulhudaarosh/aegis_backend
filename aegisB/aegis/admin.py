from django.contrib import admin
from . import models

admin.site.register(models.EmergencyContact)


@admin.register(models.ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "order", "is_active", "resource_count")
    list_editable = ("order", "is_active")
    search_fields = ("name", "description")

    def resource_count(self, obj):
        return obj.resources.count()
    resource_count.short_description = "Resources"


class ExternalLinkInline(admin.TabularInline):
    model = models.ExternalLink
    extra = 1


class QuizOptionInline(admin.TabularInline):
    model = models.QuizOption
    extra = 4


class QuizQuestionInline(admin.TabularInline):
    model = models.QuizQuestion
    extra = 1


@admin.register(models.LearningResource)
class LearningResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "resource_type", "difficulty", "category", "is_published", "order")
    list_filter = ("resource_type", "difficulty", "category", "is_published")
    list_editable = ("order", "is_published")
    search_fields = ("title", "description", "content")
    inlines = [ExternalLinkInline, QuizQuestionInline]


@admin.register(models.UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "resource", "completed", "progress_percentage", "bookmarked")
    list_filter = ("completed", "bookmarked")
    search_fields = ("user__email", "resource__title")


@admin.register(models.UserQuizAttempt)
class UserQuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "resource", "score_display", "correct_answers", "total_questions", "completed_at")
    list_filter = ("completed_at",)
    search_fields = ("user__email", "resource__title")

    def score_display(self, obj):
        return f"{obj.score:.2f}%" if obj.total_questions else "N/A"
    score_display.short_description = "Score"



admin.site.register(models.IncidentReport)

admin.site.register(models.IncidentMedia)