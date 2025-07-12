from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat_view, name='chat'),
    path('process-message/', views.process_message, name='process_message'),
    path('mood-tracker/', views.mood_tracker, name='mood_tracker'),
    path('resources/', views.resources, name='resources'),
    path('clear-chat/', views.clear_chat, name='clear_chat'),
]