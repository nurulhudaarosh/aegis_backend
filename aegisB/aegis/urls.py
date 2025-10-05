from django.urls import path
from . import views
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    # contact
    path('contacts/', views.emergency_contacts_list, name='emergency-contacts-list'),
    path('contacts/<int:pk>/', views.emergency_contact_detail, name='emergency-contact-detail'),
    path('contacts/<int:pk>/test-alert/', views.test_emergency_alert, name='test-emergency-alert'),
    path('contacts/<int:pk>/delete/', views.delete_emergency_contact, name='delete-emergency-contact'),
    path('lookup-phone/', views.lookup_phone, name='lookup-phone'),
    path('user/emergency-info/', views.user_emergency_info, name='user-emergency-info'),

    # learn
    path('learn/categories/', views.resource_categories, name='resource-categories'),
    path('learn/resources/', views.LearningResourceListView.as_view(), name='learning-resources-list'),
    path('learn/resources/<int:id>/', views.LearningResourceDetailView.as_view(), name='learning-resource-detail'),
    path('learn/resources/<int:resource_id>/bookmark/', views.toggle_bookmark, name='toggle-bookmark'),
    path('learn/resources/<int:resource_id>/quiz/submit/', views.submit_quiz, name='submit-quiz'),
    path('learn/progress/', views.user_progress, name='user-progress'),
    path('learn/quiz-history/', views.user_quiz_history, name='user-quiz-history'),
    path('learn/bookmarks/', views.bookmarked_resources, name='bookmarked-resources'),

    path('learn/categories/create/', views.create_resource_category, name='create-resource-category'),
    path('learn/resources/create/', views.create_learning_resource, name='create-learning-resource'),
    path('learn/resources/<int:resource_id>/external-links/create/', views.create_external_link, name='create-external-link'),
    path('learn/resources/<int:resource_id>/quiz-questions/create/', views.create_quiz_question, name='create-quiz-question'),
    path('learn/resources/<int:id>/delete/', views.learning_resource_delete, name='learning-resource-delete'),
    path('learn/resources/<int:resource_id>/update-visibility/', views.toggle_visibility, name='toggle-visibility'),
    path('learn/quiz-questions/<int:question_id>/options/create/', views.create_quiz_option, name='create-quiz-option'),

    path('learn/resources/<int:resource_id>/update/', views.update_learning_resource, name='update-learning-resource'),
    path('learn/quiz-questions/<int:question_id>/update/', views.update_quiz_question, name='update-quiz-question'),
    path('learn/quiz-options/<int:option_id>/update/', views.update_quiz_option, name='update-quiz-option'),
    path('learn/categories/<int:category_id>/update/', views.update_resource_category, name='update-resource-category'),
    path('learn/external-links/<int:link_id>/update/', views.update_external_link, name='update-external-link'),
    
    path('learn/resources/<int:resource_id>/delete/', views.delete_learning_resource, name='delete-learning-resource'),
    path('learn/quiz-questions/<int:question_id>/delete/', views.delete_quiz_question, name='delete-quiz-question'),
    path('learn/quiz-options/<int:option_id>/delete/', views.delete_quiz_option, name='delete-quiz-option'),
    path('learn/categories/<int:category_id>/delete/', views.delete_resource_category, name='delete-resource-category'),
    path('learn/external-links/<int:link_id>/delete/', views.delete_external_link, name='delete-external-link'),


    # incident reports

    path('reports/submit/', views.submit_incident_report, name='submit-incident'),
    path('reports/', views.IncidentReportListView.as_view(), name='incident-reports-list'),
    path('reports/<int:id>/', views.IncidentReportDetailView.as_view(), name='incident-report-detail'),
    path('reports/<int:incident_id>/media/', views.upload_incident_media, name='upload-incident-media'),
    path('reports/<int:incident_id>/update-status/', views.update_incident_status, name='upload-incident-status'),
    path('reports/statistics/', views.incident_statistics, name='incident-statistics'),
    path('reports/recent/', views.recent_incidents, name='recent-incidents'),

    # safety check

    path('safety/settings/', views.safety_settings, name='safety-settings'),
    path('safety/check-in/manual/', views.manual_check_in, name='manual-check-in'),
    path('safety/alert/test/', views.test_emergency_alert, name='test-emergency-alert'),
    path('safety/statistics/', views.safety_statistics, name='safety-statistics'),
    path('safety/history/check-ins/', views.check_in_history, name='check-in-history'),
    path('safety/history/alerts/', views.alert_history, name='alert-history'),

    # silent capture

    path('evidence/submit/', views.submit_video_evidence, name='submit-video-evidence'),
    path('evidence/<int:evidence_id>/upload/', views.upload_video_file, name='upload-video-file'),
    path('evidence/list/', views.list_video_evidence, name='list-video-evidence'),
    path('evidence/<int:evidence_id>/', views.get_video_evidence, name='get-video-evidence'),
    path('evidence/<int:evidence_id>/delete/', views.delete_video_evidence, name='delete-video-evidence'),
    path('evidence/statistics/', views.video_evidence_statistics, name='video-evidence-statistics'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)