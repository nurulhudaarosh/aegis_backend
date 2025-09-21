from django.urls import path
from . import views

urlpatterns = [
    path('contacts/', views.emergency_contacts_list, name='emergency-contacts-list'),
    path('contacts/<int:pk>/', views.emergency_contact_detail, name='emergency-contact-detail'),
    path('contacts/<int:pk>/test-alert/', views.test_emergency_alert, name='test-emergency-alert'),
    path('contacts/<int:pk>/delete/', views.delete_emergency_contact, name='delete-emergency-contact'),
    path('lookup-phone/', views.lookup_phone, name='lookup-phone'),
    path('user/emergency-info/', views.user_emergency_info, name='user-emergency-info'),
]