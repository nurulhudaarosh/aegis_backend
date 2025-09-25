from django.urls import path
from . import views

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

    # Insert endpoints
    path('learn/categories/create/', views.create_resource_category, name='create-resource-category'),
    path('learn/resources/create/', views.create_learning_resource, name='create-learning-resource'),
    path('learn/resources/<int:resource_id>/external-links/create/', views.create_external_link, name='create-external-link'),
    path('learn/resources/<int:resource_id>/quiz-questions/create/', views.create_quiz_question, name='create-quiz-question'),
    path('learn/quiz-questions/<int:question_id>/options/create/', views.create_quiz_option, name='create-quiz-option'),


    # incident reports

    path('reports/submit/', views.submit_incident_report, name='submit-incident'),
    path('reports/', views.IncidentReportListView.as_view(), name='incident-reports-list'),
    path('reports/<int:id>/', views.IncidentReportDetailView.as_view(), name='incident-report-detail'),
    path('reports/<int:incident_id>/media/', views.upload_incident_media, name='upload-incident-media'),
    path('reports/statistics/', views.incident_statistics, name='incident-statistics'),
    path('reports/recent/', views.recent_incidents, name='recent-incidents'),
]