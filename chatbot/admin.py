from django.contrib import admin
from .models import UserProfile, Conversation, Message, MoodEntry, SupportResource

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'age', 'consent_given', 'created_at']
    list_filter = ['consent_given', 'privacy_accepted', 'created_at']
    search_fields = ['user__username', 'user__email']

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'started_at', 'is_active']
    list_filter = ['is_active', 'started_at']
    search_fields = ['session_id', 'user__username']
    readonly_fields = ['session_id']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation', 'message_type', 'content_preview', 'timestamp']
    list_filter = ['message_type', 'timestamp']
    search_fields = ['content']
    readonly_fields = ['timestamp']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'

@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'mood_level', 'created_at']
    list_filter = ['mood_level', 'created_at']
    search_fields = ['user__username', 'notes']

@admin.register(SupportResource)
class SupportResourceAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_emergency', 'created_at']
    list_filter = ['category', 'is_emergency', 'created_at']
    search_fields = ['title', 'description']