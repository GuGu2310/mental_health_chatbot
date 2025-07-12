from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from chatbot.models import Conversation, Message

class Command(BaseCommand):
    help = 'Cleanup old conversations for privacy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete conversations older than specified days (default: 30)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get old conversations
        old_conversations = Conversation.objects.filter(
            started_at__lt=cutoff_date
        )
        
        conversation_count = old_conversations.count()
        message_count = Message.objects.filter(
            conversation__in=old_conversations
        ).count()
        
        # Delete old conversations (messages will be deleted via cascade)
        old_conversations.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Deleted {conversation_count} conversations and {message_count} messages '
                f'older than {days} days'
            )
        )