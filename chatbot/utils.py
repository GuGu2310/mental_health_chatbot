import re
import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import Conversation, Message

logger = logging.getLogger(__name__)

def clean_message_content(content):
    """Clean and sanitize message content"""
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content.strip())
    
    # Remove potential harmful content
    content = re.sub(r'<script.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'<.*?>', '', content)  # Remove HTML tags
    
    return content

def analyze_conversation_sentiment(conversation):
    """Analyze overall sentiment of a conversation"""
    messages = Message.objects.filter(
        conversation=conversation,
        message_type='user',
        sentiment_score__isnull=False
    )
    
    if not messages:
        return None
    
    total_sentiment = sum(msg.sentiment_score for msg in messages)
    return total_sentiment / len(messages)

def get_conversation_stats(conversation):
    """Get statistics for a conversation"""
    messages = Message.objects.filter(conversation=conversation)
    user_messages = messages.filter(message_type='user')
    bot_messages = messages.filter(message_type='bot')
    
    return {
        'total_messages': messages.count(),
        'user_messages': user_messages.count(),
        'bot_messages': bot_messages.count(),
        'duration': conversation.ended_at - conversation.started_at if conversation.ended_at else None,
        'avg_sentiment': analyze_conversation_sentiment(conversation)
    }

def send_crisis_alert_email(user_message, conversation_id):
    """Send alert email when crisis is detected"""
    if not hasattr(settings, 'CRISIS_ALERT_EMAIL'):
        return
    
    subject = 'Crisis Alert - Mental Health Chatbot'
    message = f"""
    Crisis keywords detected in conversation.
    
    Conversation ID: {conversation_id}
    Timestamp: {timezone.now()}
    Message excerpt: {user_message[:100]}...
    
    Please review if intervention is needed.
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.CRISIS_ALERT_EMAIL],
            fail_silently=False,
        )
        logger.info(f"Crisis alert email sent for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Failed to send crisis alert email: {e}")

def get_user_mood_trend(user, days=7):
    """Get user's mood trend over specified days"""
    from .models import MoodEntry
    
    if not user or not user.is_authenticated:
        return None
    
    start_date = timezone.now() - timedelta(days=days)
    mood_entries = MoodEntry.objects.filter(
        user=user,
        created_at__gte=start_date
    ).order_by('created_at')
    
    if not mood_entries:
        return None
    
    moods = [entry.mood_level for entry in mood_entries]
    return {
        'average': sum(moods) / len(moods),
        'trend': 'improving' if moods[-1] > moods[0] else 'declining' if moods[-1] < moods[0] else 'stable',
        'entries': len(moods)
    }

def format_phone_number(phone):
    """Format phone number for display"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"1-({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone

def validate_mood_entry(mood_level, notes=""):
    """Validate mood entry data"""
    errors = []
    
    if not isinstance(mood_level, int) or mood_level not in range(1, 6):
        errors.append("Mood level must be between 1 and 5")
    
    if notes and len(notes) > 1000:
        errors.append("Notes cannot exceed 1000 characters")
    
    return errors

class ConversationManager:
    """Helper class for managing conversations"""
    
    @staticmethod
    def end_conversation(conversation):
        """End a conversation"""
        conversation.ended_at = timezone.now()
        conversation.is_active = False
        conversation.save()
        logger.info(f"Conversation {conversation.session_id} ended")
    
    @staticmethod
    def get_active_conversations():
        """Get all active conversations"""
        return Conversation.objects.filter(is_active=True)
    
    @staticmethod
    def cleanup_inactive_conversations(hours=24):
        """Clean up conversations inactive for specified hours"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        inactive_conversations = Conversation.objects.filter(
            is_active=True,
            started_at__lt=cutoff_time
        )
        
        count = inactive_conversations.count()
        inactive_conversations.update(is_active=False, ended_at=timezone.now())
        
        logger.info(f"Cleaned up {count} inactive conversations")
        return count