from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Conversation, Message, MoodEntry, SupportResource
from .ai_processor import MentalHealthChatbot
from .forms import CustomUserCreationForm
import json
import uuid 
import logging
from django.utils import timezone 

logger = logging.getLogger(__name__)

def index(request):
    """Landing page"""
    return render(request, 'index.html')

def chat_view(request):
    """Main chat interface"""
    # Create or get conversation session
    session_id = request.session.get('conversation_id')
    if not session_id:
        conversation = Conversation.objects.create(
            user=request.user if request.user.is_authenticated else None
        )
        request.session['conversation_id'] = str(conversation.session_id)
    else:
        try:
            conversation = Conversation.objects.get(session_id=session_id)
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create(
                user=request.user if request.user.is_authenticated else None
            )
            request.session['conversation_id'] = str(conversation.session_id)

    # Get conversation history
    messages = Message.objects.filter(conversation=conversation).order_by('timestamp')

    return render(request, 'chatbot/chat.html', {
        'messages': messages,
        'conversation_id': conversation.session_id
    })

@csrf_exempt
@require_http_methods(["POST"])
def process_message(request):
    """Process user message and return bot response"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'error': 'No message provided'}, status=400)

        # Get or create conversation based on session_id
        session_id = request.session.get('conversation_id')
        if not session_id:
            conversation = Conversation.objects.create(
                user=request.user if request.user.is_authenticated else None
            )
            request.session['conversation_id'] = str(conversation.session_id)
        else:
            try:
                conversation = Conversation.objects.get(session_id=session_id)
            except Conversation.DoesNotExist:
                # If a session_id exists but the conversation doesn't, create a new one
                conversation = Conversation.objects.create(
                    user=request.user if request.user.is_authenticated else None
                )
                request.session['conversation_id'] = str(conversation.session_id)

        # Save user message
        user_msg = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=user_message
        )

        # Generate bot response
        chatbot = MentalHealthChatbot()

        # Get conversation history for context (last 10 messages)
        recent_messages = Message.objects.filter(
            conversation=conversation
        ).order_by('-timestamp')[:10]

        conversation_history = []
        for msg in reversed(recent_messages):
            messages_for_history = {
                'role': 'user' if msg.message_type == 'user' else 'assistant',
                'content': msg.content
            }
            conversation_history.append(messages_for_history)

        response = chatbot.generate_response(user_message, conversation_history)

        # Save bot response
        bot_msg = Message.objects.create(
            conversation=conversation,
            message_type='bot',
            content=response['message'],
            sentiment_score=response.get('sentiment')
        )

        # Get support resources if crisis detected
        support_resources = []
        if response.get('is_crisis'):
            support_resources = list(SupportResource.objects.filter(
                is_emergency=True
            ).values('title', 'description', 'phone_number', 'url'))

        return JsonResponse({
            'bot_response': response['message'],
            'is_crisis': response.get('is_crisis', False),
            'sentiment': response.get('sentiment'),
            'support_resources': support_resources,
            'timestamp': bot_msg.timestamp.isoformat(),
            'message_id': bot_msg.id
        })

    except json.JSONDecodeError:
        logger.error(f"JSON Decode Error in process_message. Request Body: {request.body.decode('utf-8')}")
        return JsonResponse({'error': 'Invalid JSON format in request.'}, status=400)
    except Exception as e:
        logger.error(f"Unhandled error in process_message: {e}", exc_info=True) # exc_info=True to log full traceback
        return JsonResponse({'error': 'Internal server error processing message.'}, status=500)

@login_required
def mood_tracker(request):
    """Mood tracking interface"""
    # Ensure a session_id exists for the current user/session for consistent tracking
    current_session_id_str = request.session.get('conversation_id')
    if not current_session_id_str:
        # If no conversation_id yet, generate a new UUID for this session
        new_session_uuid = uuid.uuid4()
        request.session['conversation_id'] = str(new_session_uuid)
        current_session_id_str = str(new_session_uuid)

    # Convert session_id string to UUID object for database queries
    current_session_uuid_obj = uuid.UUID(current_session_id_str)

    if request.method == 'POST':
        try:
            mood_level = int(request.POST.get('mood_level'))
            notes = request.POST.get('notes', '')

            if mood_level not in [1, 2, 3, 4, 5]:
                return JsonResponse({'error': 'Invalid mood level'}, status=400)

            # Try to link to an existing Conversation if one exists for this session
            conversation_obj = None
            if current_session_id_str:
                try:
                    conversation_obj = Conversation.objects.get(session_id=current_session_uuid_obj)
                except Conversation.DoesNotExist:
                    pass # It's okay if no conversation object is found for this session_id

            MoodEntry.objects.create(
                user=request.user if request.user.is_authenticated else None, # Link to User if logged in
                conversation=conversation_obj, # Link to Conversation if found
                session_id=current_session_uuid_obj, # Always link to session for anonymous tracking
                mood_level=mood_level,
                notes=notes
            )

            # Important: After a successful POST, we usually redirect or return data.
            # Returning JSON here is correct for AJAX.
            return JsonResponse({'status': 'success', 'message': 'Mood recorded successfully!'})
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid mood data: {e}, Request POST: {request.POST}")
            return JsonResponse({'error': 'Invalid mood data provided.'}, status=400)
        except Exception as e:
            logger.error(f"Unhandled error saving mood entry: {e}", exc_info=True) # Log full traceback
            return JsonResponse({'error': 'Internal server error when saving mood.'}, status=500)

    # --- GET recent mood entries for display ---
    recent_moods = []
    if request.user.is_authenticated:
        # For logged-in users, retrieve their own entries (regardless of session_id, as user is primary)
        recent_moods = MoodEntry.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10] # Get latest 10 entries
    else:
        # For anonymous users, retrieve entries associated with their specific session_id
        # Ensure it's entries *not* linked to a user, to avoid mixing anonymous with authenticated
        recent_moods = MoodEntry.objects.filter(
            session_id=current_session_uuid_obj,
            user__isnull=True 
        ).order_by('-created_at')[:10] # Get latest 10 entries

    return render(request, 'chatbot/mood_tracker.html', {
        'recent_moods': recent_moods
    })

@login_required
def resources(request):
    """Mental health resources page"""
    emergency_resources = SupportResource.objects.filter(is_emergency=True)
    general_resources = SupportResource.objects.filter(is_emergency=False)

    return render(request, 'chatbot/resources.html', {
        'emergency_resources': emergency_resources,
        'general_resources': general_resources
    })

def clear_chat(request):
    """Clear current chat session"""
    session_id = request.session.get('conversation_id')
    if session_id:
        try:
            # Mark the conversation as inactive if it exists
            conversation = Conversation.objects.get(session_id=uuid.UUID(session_id)) # Convert to UUID
            conversation.is_active = False
            conversation.ended_at = timezone.now() # Ensure ended_at is set for cleanup
            conversation.save()
        except Conversation.DoesNotExist:
            pass # No active conversation for this session_id, nothing to mark inactive

        # Remove the conversation_id from the session to start fresh
        if 'conversation_id' in request.session:
            del request.session['conversation_id']

    return redirect('chat')

def register(request):
    """User registration"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'chatbot/register.html', {'form': form})

def login_view(request):
    """User login"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('chat')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'chatbot/login.html', {'form': form})

def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')

@login_required
def delete_account(request):
    """Delete user account"""
    if request.method == 'POST':
        user = request.user
        username = user.username
        user.delete()
        messages.success(request, f'Account {username} has been deleted successfully.')
        return redirect('index')
    return render(request, 'chatbot/delete_account.html')

@login_required
def delete_mood_entry(request, mood_id):
    """Delete a specific mood entry"""
    mood_entry = get_object_or_404(MoodEntry, id=mood_id, user=request.user)

    if request.method == 'POST':
        mood_entry.delete()
        return JsonResponse({'status': 'success', 'message': 'Mood entry deleted successfully!'})

    return JsonResponse({'error': 'Invalid request method'}, status=405)

# Updated admin functionality