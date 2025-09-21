from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_user, name='register'),
    path('login/', views.login_user, name='login'),
    path('profile/', views.get_user_profile, name='profile'),
    path('profile/picture/', views.update_profile_picture, name='update-profile-picture'),
    path('profile/picture/delete/', views.delete_profile_picture, name='update-profile-picture'),
    path('auth-status/', views.check_auth_status, name='auth_status'),
]