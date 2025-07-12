from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat_view, name='chat'),
    path('process-message/', views.process_message, name='process_message'),
    path('mood-tracker/', views.mood_tracker, name='mood_tracker'),
    path('resources/', views.resources, name='resources'),
    path('clear-chat/', views.clear_chat, name='clear_chat'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('delete-account/', views.delete_account_view, name='delete_account'),
]