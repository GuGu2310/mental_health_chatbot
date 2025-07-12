from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Conversation, Message, MoodEntry, SupportResource
from .ai_processor import MentalHealthChatbot
import json

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.conversation = Conversation.objects.create(user=self.user)

    def test_conversation_creation(self):
        """Test conversation model creation"""
        self.assertTrue(self.conversation.session_id)
        self.assertTrue(self.conversation.is_active)
        self.assertEqual(self.conversation.user, self.user)

    def test_message_creation(self):
        """Test message model creation"""
        message = Message.objects.create(
            conversation=self.conversation,
            message_type='user',
            content='Hello, I need help'
        )
        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.message_type, 'user')

    def test_mood_entry_creation(self):
        """Test mood entry model creation"""
        mood = MoodEntry.objects.create(
            user=self.user,
            conversation=self.conversation,
            mood_level=3,
            notes='Feeling okay today'
        )
        self.assertEqual(mood.mood_level, 3)
        self.assertEqual(mood.user, self.user)

class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_index_view(self):
        """Test index page loads"""
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mental Health Support')

    def test_chat_view(self):
        """Test chat page loads"""
        response = self.client.get(reverse('chat'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'chat-messages')

    def test_process_message_post(self):
        """Test message processing"""
        data = {'message': 'Hello, I need help'}
        response = self.client.post(
            reverse('process_message'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('bot_response', response_data)

    def test_mood_tracker_view(self):
        """Test mood tracker page"""
        response = self.client.get(reverse('mood_tracker'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mood Tracker')

    def test_resources_view(self):
        """Test resources page"""
        response = self.client.get(reverse('resources'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mental Health Resources')

class AIProcessorTests(TestCase):
    def setUp(self):
        self.chatbot = MentalHealthChatbot()

    def test_crisis_detection(self):
        """Test crisis keyword detection"""
        crisis_message = "I want to kill myself"
        self.assertTrue(self.chatbot.detect_crisis(crisis_message))
        
        normal_message = "I'm feeling sad today"
        self.assertFalse(self.chatbot.detect_crisis(normal_message))

    def test_sentiment_analysis(self):
        """Test sentiment analysis"""
        positive_message = "I'm feeling great and happy!"
        sentiment = self.chatbot.analyze_sentiment(positive_message)
        self.assertGreater(sentiment, 0)

        negative_message = "I'm feeling terrible and sad"
        sentiment = self.chatbot.analyze_sentiment(negative_message)
        self.assertLess(sentiment, 0)

    def test_response_generation(self):
        """Test response generation"""
        message = "Hello, I need someone to talk to"
        response = self.chatbot.generate_response(message)
        
        self.assertIn('message', response)
        self.assertIsInstance(response['message'], str)
        self.assertIn('is_crisis', response)

    def test_crisis_response(self):
        """Test crisis response"""
        crisis_message = "I want to end my life"
        response = self.chatbot.generate_response(crisis_message)
        
        self.assertTrue(response['is_crisis'])
        self.assertIn('988', response['message'])

class FormTests(TestCase):
    def test_mood_entry_form_valid(self):
        """Test valid mood entry form"""
        from .forms import MoodEntryForm
        
        form_data = {
            'mood_level': 3,
            'notes': 'Feeling okay today'
        }
        form = MoodEntryForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_mood_entry_form_invalid(self):
        """Test invalid mood entry form"""
        from .forms import MoodEntryForm
        
        form_data = {
            'mood_level': 6,  # Invalid range
            'notes': 'Test note'
        }
        form = MoodEntryForm(data=form_data)
        self.assertFalse(form.is_valid())

class IntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create test resources
        SupportResource.objects.create(
            title='Test Crisis Line',
            description='Test crisis support',
            phone_number='988',
            category='crisis',
            is_emergency=True
        )

    def test_full_chat_workflow(self):
        """Test complete chat workflow"""
        # Start chat
        response = self.client.get(reverse('chat'))
        self.assertEqual(response.status_code, 200)
        
        # Send message
        data = {'message': 'I need help with anxiety'}
        response = self.client.post(
            reverse('process_message'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertIn('bot_response', response_data)
        self.assertFalse(response_data['is_crisis'])

    def test_crisis_workflow(self):
        """Test crisis detection workflow"""
        # Send crisis message
        data = {'message': 'I want to hurt myself'}
        response = self.client.post(
            reverse('process_message'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['is_crisis'])
        self.assertGreater(len(response_data['support_resources']), 0)

    def test_mood_tracking_workflow(self):
        """Test mood tracking workflow"""
        # Submit mood
        data = {
            'mood_level': 4,
            'notes': 'Had a good day'
        }
        response = self.client.post(reverse('mood_tracker'), data)
        self.assertEqual(response.status_code, 200)
        
        # Check mood was saved
        mood_entries = MoodEntry.objects.all()
        self.assertEqual(mood_entries.count(), 1)
        self.assertEqual(mood_entries.first().mood_level, 4)