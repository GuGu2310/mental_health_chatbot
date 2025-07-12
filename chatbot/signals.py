from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, Conversation, Message
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile when User is created"""
    if created:
        UserProfile.objects.create(user=instance)
        logger.info(f"UserProfile created for user: {instance.username}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=Message)
def log_message_created(sender, instance, created, **kwargs):
    """Log when messages are created"""
    if created:
        logger.info(f"Message created: {instance.message_type} - {instance.content[:50]}...")

@receiver(post_delete, sender=Conversation)
def log_conversation_deleted(sender, instance, **kwargs):
    """Log when conversations are deleted"""
    logger.info(f"Conversation deleted: {instance.session_id}")