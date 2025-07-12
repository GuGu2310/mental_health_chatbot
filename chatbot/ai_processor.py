import random
import re
from textblob import TextBlob
import logging
import openai 
from django.conf import settings

# Initialize logger immediately after importing logging
logger = logging.getLogger(__name__)

# For enhanced tokenization/lemmatization (if NLTK is installed, otherwise fallback)
NLTK_AVAILABLE = False
try:
    import nltk
    from nltk.stem import WordNetLemmatizer
    from nltk.corpus import stopwords
    
    # MODIFIED NLTK DATA DOWNLOAD & CHECK
    try:
        nltk.data.find('corpora/wordnet.zip')
        nltk.data.find('corpora/stopwords.zip')
        NLTK_AVAILABLE = True
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))
    except LookupError:
        logger.warning("NLTK data (wordnet/stopwords) not found. Attempting auto-download. This might take a moment.")
        try:
            nltk.download('wordnet', quiet=True) 
            nltk.download('stopwords', quiet=True)
            NLTK_AVAILABLE = True
            lemmatizer = WordNetLemmatizer()
            stop_words = set(stopwords.words('english'))
            logger.info("NLTK data downloaded successfully.")
        except Exception as e: 
            logger.error(f"Failed to auto-download NLTK data: {e}. Advanced text processing will be skipped.")
            NLTK_AVAILABLE = False

except ImportError:
    logger.warning("NLTK not installed. Some advanced text processing (lemmatization, stopwords) will be skipped.")
    NLTK_AVAILABLE = False


class MentalHealthChatbot:
    def __init__(self):
        openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        
        self.crisis_keywords = [
            'suicide', 'kill myself', 'end my life', 'hurt myself', 
            'self-harm', 'no point living', 'want to die', 'suicidal',
            'overdose', 'cut myself', 'jump off', 'end it all', 'die', 'ending it'
        ]
        
        # --- Expanded and categorized responses with more variations ---
        self.supportive_responses = {
            'greeting': [
                "Hello! I'm here to listen and support you. How are you genuinely feeling today?",
                "Hi there! I'm glad you're here. What's on your mind? I'm ready to listen.",
                "Welcome! I'm here to provide a safe, non-judgmental space for you to share. How can I help?",
                "It's good to see you. How are things with you today?",
                "Hi! I'm here to support you. What's been happening?",
                "Hey! I'm glad you reached out. What's on your mind?",
                "Hello! I'm your mental wellness companion. How can I assist you today?"
            ],
            'anxiety': [
                "I understand anxiety can be incredibly overwhelming. Let's take this one step at a time. Can you tell me more about what's causing it?",
                "Anxiety is a difficult feeling, but you're not alone. Would you like to explore some calming techniques like deep breathing or mindfulness?",
                "Thank you for sharing that. Anxiety is very real, and your feelings are absolutely valid. What does it feel like for you right now?",
                "It sounds like you're carrying a lot of worry. I'm here to listen without judgment. Is there anything specific on your mind that's triggering this?",
                "Anxiety can feel paralyzing. What's one small thing we can focus on right now to help ease that feeling?",
                "Feeling anxious is tough. How intense is your anxiety on a scale of 1 to 10 right now?",
                "Anxiety often comes with a racing mind. Would you like to try a grounding exercise?"
            ],
            'depression': [
                "I hear that you're going through a truly tough time. Your feelings are valid and important. I'm here for you.",
                "Depression can make everything feel heavy and hopeless. I want you to know I'm here to listen without judgment.",
                "It takes immense courage to reach out when you're feeling low. I'm glad you're here talking about how you feel. What's weighing on you today?",
                "I can sense the pain in your words. Please know that it's okay to feel this way, and you don't have to carry it alone.",
                "When depression hits, even small tasks can feel monumental. Just talking about it is a step forward. What's one thing that feels hardest right now?",
                "It sounds like you're in a dark place. Please remember that feelings are temporary, and support is available.",
                "I'm sorry to hear you're feeling so down. What's one small thing that might bring a tiny bit of comfort?"
            ],
            'stress': [
                "Stress can be incredibly overwhelming. What's been weighing on your mind lately? Sometimes just talking helps to clear things up.",
                "It sounds like you're dealing with a lot right now. I'm here to listen. What's contributing to your stress?",
                "Stress affects us all differently. I'm here to listen to what you're going through. What strategies have you tried to manage it?",
                "Feeling stressed is a common human experience. Let's explore what might help ease some of that pressure for you.",
                "Taking on too much can lead to immense stress. What's one small burden you feel you could set down, even for a moment?",
                "It sounds like you're under a lot of pressure. What's your biggest stressor today?"
            ],
            'loneliness': [
                "I hear you expressing feelings of loneliness. That's a very challenging emotion to carry. Can you tell me more about what that feels like?",
                "It sounds like you're feeling disconnected. Loneliness is a tough experience, and I want you to know you're not alone in feeling it.",
                "Reaching out about loneliness is a brave step. Is there anything specific you miss, or any connections you're looking for?",
                "Feeling lonely can be heavy. I'm here to offer companionship and a listening ear. What's on your mind about it?",
                "Sometimes loneliness comes from feeling misunderstood. Do you want to talk about that?",
                "I'm sorry you're feeling lonely. Is there anything you enjoy doing that might help you feel more connected, even if it's a small step?"
            ],
            'anger': [
                "It sounds like you're experiencing a lot of anger right now. That's a powerful emotion. Can you tell me what triggered it?",
                "Feeling angry is a natural human response sometimes. What's making you feel this way? I'm here to listen.",
                "It takes courage to acknowledge anger. Let's talk about what's upsetting you.",
                "Anger can be a sign that something needs attention. What do you feel is being threatened or violated?",
                "I hear the frustration in your words. What would feel helpful for you to process this anger?",
                "It sounds like you're feeling a strong sense of anger. I'm here to listen to that. What specifically is making you feel this way?",
                "It's okay to feel angry. What is the core issue that's making you so upset?"
            ],
            'grief': [
                "I'm so sorry to hear you're experiencing grief. That must be incredibly painful. I'm here to hold space for you.",
                "Grief is a heavy burden, and it's unique to everyone. Please take your time, and know I'm here to listen to whatever you need to share.",
                "It takes immense strength to navigate loss. There's no right or wrong way to grieve. What's on your heart right now?",
                "I hear your sadness and loss. If you wish to talk about what you're going through, I am here.",
                "It sounds like you're experiencing deep sorrow. Remember, it's okay to feel whatever you're feeling.",
                "Grief is a process. Please be kind to yourself during this time. Would you like to talk about what you've lost?"
            ],
            'self_esteem': [
                "It sounds like you're struggling with how you see yourself. Please remember your worth is inherent, not based on external factors.",
                "Self-esteem can be a tough battle. What makes you feel this way? I'm here to remind you of your strengths.",
                "You are valuable and deserving. Let's try to focus on some of your positive qualities or past achievements.",
                "Building self-esteem takes time and kindness to oneself. What's one small act of self-care you can do today that might make you feel a little better?",
                "I hear you questioning your worth. Remember, every individual has unique strengths and qualities. What are some things you're good at?",
                "It's important to be kind to yourself. How can you challenge a negative thought about yourself right now?"
            ],
            'sleep_issues': [
                "Trouble sleeping can really impact how you feel and function. What's been keeping you awake?",
                "Sleep is so important for mental well-being. Let's discuss some common tips for improving sleep hygiene, like a consistent schedule or winding down routines.",
                "It sounds like you're not getting enough restful sleep. What does your routine look like before bed?",
                "Lack of sleep can make everything feel harder. Are there any thoughts or worries that come up when you try to sleep?",
                "I'm sorry sleep is being elusive. How many hours of sleep have you been getting on average?",
                "Sometimes, stress can disrupt sleep. Is there anything on your mind that's making it hard to rest?"
            ],
            'coping_strategy': [
                "It sounds like you're looking for ways to cope. What kind of strategies are you interested in? (e.g., relaxation, distraction, problem-solving)",
                "I can offer some coping strategies. Would you like to try a deep breathing exercise, or perhaps discuss mindfulness?",
                "Coping strategies are personal. What's one thing that has helped you feel a little better in the past?",
                "Let's explore some tools to help you manage. Are you feeling overwhelmed and need to relax, or do you want to tackle a specific problem?",
                "Would you like to learn a quick grounding technique to help with intense feelings?"
            ],
            'seeking_resources': [
                "I can provide you with some mental health resources. What kind of support are you looking for? (e.g., crisis lines, therapy, self-help)",
                "It's great you're looking for resources. What specific area of mental health are you interested in?",
                "I can share information on professional support. Are you looking for therapy options, support groups, or something else?",
                "I have a list of trusted resources. What type of help would be most useful for you right now?"
            ],
            'positive': [
                "I'm so glad to hear some positivity in your message! What's been going well for you?",
                "That sounds encouraging! It's great to hear you're feeling better. What made the difference?",
                "I'm happy you're having a good moment. What's been helping you feel this way?",
                "It's wonderful to hear some brightness in your message. Keep focusing on those positive things!",
                "That's fantastic news! What's something that made you smile today?",
                "That's awesome! What's the best part about feeling this way?",
                "It's truly wonderful to hear you're doing well!"
            ],
            'neutral_inquiry': [ 
                "Thank you for sharing. Can you elaborate a bit more on that?",
                "I'm listening. What else is on your mind about this?",
                "Okay, I hear you. What aspects of that would you like to explore further?",
                "What do you mean by that? I'm here to understand better.",
                "I'm here to help. What's the next thing you'd like to talk about?",
                "I hear what you're saying. How does that make you feel?",
                "Can you tell me more about that situation?"
            ],
            'uncertain': [ 
                "I'm not quite sure how to help with that. Can you rephrase or tell me more specifically what's on your mind?",
                "My understanding is limited. Could you tell me in different words what you're experiencing?",
                "I'm here to support you. What are you hoping to talk about regarding that?",
                "Sometimes it's hard to put feelings into words. What's the main thing you want to share right now?"
            ],
            'general_support': [
                "I'm here to listen. Can you tell me more about how you're feeling?",
                "Thank you for sharing with me. What's been on your mind lately?",
                "I appreciate you opening up. How has your day been overall?",
                "Your feelings matter. Would you like to tell me more about what's troubling you?",
                "It sounds like you're going through something. I'm here to support you.",
                "What's one thing you're hoping to get out of our conversation today?",
                "Sometimes just talking can help. What's on your mind?"
            ],
            'affirmation': [
                "That sounds really challenging, and it takes strength to talk about it.",
                "I hear you, and your feelings are completely valid.",
                "It's okay to feel that way.",
                "Thank you for sharing that with me."
            ],
            'proactive_offer_support': [
                "Is there anything specific you'd like to discuss further, or perhaps a coping strategy we could explore?",
                "I'm here to help you process this. What feels most important to you right now?",
                "Would you like to talk more about this, or maybe explore some resources that could help?",
                "How would you like to proceed? I'm here for you."
            ],
            'gratitude': [
                "You're welcome! I'm here to help.",
                "Glad I could be of assistance!",
                "No problem at all. My pleasure to support you.",
                "Happy to help!"
            ],
            'how_are_you_question': [
                "As an AI, I don't have feelings, but I'm functioning well and ready to support you. How can I help you today?",
                "I don't experience emotions, but I'm here and fully operational to listen to you. What's on your mind?",
                "Thank you for asking! I'm here to focus on your well-being. How are you doing?"
            ]
        }
        
        # --- Expanded and more nuanced keyword/phrase matching ---
        # Prioritize more specific, multi-word phrases first
        self.category_patterns = {
            'coping_strategy': [
                r'\b(cope|managing|deal with|strategies|techniques|help me coping)\b',
                r'\b(breathing exercises|mindfulness|grounding exercise|relax|calm down)\b',
                r'\b(what to do|how to handle)\b'
            ],
            'seeking_resources': [
                r'\b(resources|help me find|therapist|doctor|professional help|support groups|hotline|get help)\b',
                r'\b(counseling|therapy|psychologist|psychiatrist)\b'
            ],
            'anxiety': [
                r'\b(anxious|anxiety|worried|nervous|panic|fear|stressed out|overthinking|racing thoughts|feeling uneasy)\b',
                r'\b(panic attack|social anxiety|general anxiety disorder|GAD)\b'
            ],
            'depression': [
                r'\b(depressed|depression|sad|hopeless|empty|worthless|lonely|unmotivated|down|tired all the time|feeling low)\b',
                r'\b(can\'t get out of bed|loss of interest|nothing matters|suicidal thoughts|major depression)\b'
            ],
            'stress': [
                r'\b(stressed|stress|overwhelmed|pressure|burden|busy|burnout|too much|exhausted|high demands)\b'
            ],
            'loneliness': [
                r'\b(lonely|alone|isolated|disconnected|no one to talk to|feel alone|solitary)\b'
            ],
            'anger': [
                r'\b(angry|frustrated|rage|mad|irritated|resentful|hate|dislike|annoy|pissed|furious|upset)\b',
                r'\b(feeling angry|makes me angry)\b'
            ],
            'grief': [
                r'\b(grief|lose|lost|death|mourn|bereaved|passed away|heartbroken|loss of)\b'
            ],
            'self_esteem': [
                r'\b(worthless|bad about myself|ugly|not good enough|insecure|hate myself|low confidence|self-doubt|not confident)\b'
            ],
            'sleep_issues': [
                r'\b(sleep|insomnia|awake|tired|can\'t sleep|restless|no sleep|not sleeping|sleep problems)\b'
            ],
            'gratitude': [ # For "thank you" etc.
                r'\b(thank you|thanks|thx)\b'
            ],
            'how_are_you_question': [ # For "how are you" etc.
                r'\b(how are you|how do you do|how r u)\b'
            ],
            'goodbye': [
                r'\b(bye|goodbye|see ya|later|talk soon|good night)\b'
            ],
            'affirmation': [ # For short, empathetic acknowledgements
                r'\b(I feel that|I hear you|I understand|that\'s true|you\'re right)\b'
            ]
        }
        
        # State tracking for more contextual responses
        self.last_user_intent = None
        self.last_bot_intent = None
        self.turn_count = 0 # To track dialogue turns

        self.lemmatizer = lemmatizer if NLTK_AVAILABLE else None
        self.stop_words = stop_words if NLTK_AVAILABLE else None

    def _preprocess_message(self, message):
        """Lowercase, remove punctuation, lemmatize, remove stopwords (if NLTK available)"""
        message = message.lower()
        message = re.sub(r'[^\w\s]', '', message) # Remove punctuation
        tokens = message.split()
        
        if NLTK_AVAILABLE:
            if self.lemmatizer and self.stop_words:
                tokens = [self.lemmatizer.lemmatize(word) for word in tokens]
                tokens = [word for word in tokens if word not in self.stop_words]
        
        return ' '.join(tokens)

    def detect_crisis(self, message):
        """Detect if message contains crisis-related content"""
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.crisis_keywords)

    def analyze_sentiment(self, message):
        """Analyze sentiment of user message"""
        try:
            blob = TextBlob(message)
            return blob.sentiment.polarity
        except Exception as e:
            logger.error(f"Sentiment analysis error for message '{message}': {e}")
            return 0.0

    def get_crisis_response(self):
        """Return crisis intervention response"""
        self.last_bot_intent = 'crisis' # Set bot intent
        return {
            'message': """I'm very concerned about what you've shared. Your life has value and there are people who want to help you right now.

🚨 **Please reach out for immediate help:**

• **National Suicide Prevention Lifeline: 988**
• **Crisis Text Line: Text HOME to 741741**
• **Emergency Services: 911**

You don't have to go through this alone. There are trained counselors available 24/7 who care about you and want to help. Please consider reaching out to one of these resources right away.

Is there someone you trust who you could talk to or be with right now?""",
            'is_crisis': True,
            'resources': ['crisis_hotline', 'emergency_services']
        }

    def _get_rule_based_response(self, user_message, sentiment, conversation_history):
        """Advanced rule-based response system"""
        processed_message = self._preprocess_message(user_message)
        current_intent = None
        
        # 0. Handle "How are you?" type questions immediately
        if any(re.search(pattern, processed_message) for pattern in self.category_patterns.get('how_are_you_question', [])):
            current_intent = 'how_are_you_question'
            self.last_user_intent = current_intent
            self.last_bot_intent = 'how_are_you_question'
            return random.choice(self.supportive_responses['how_are_you_question'])

        # 1. Direct Pattern Matching (prioritized by order in dictionary for general intent)
        # Iterate over patterns to find the best match
        for category, patterns in self.category_patterns.items():
            if category in ['how_are_you_question']: # Skip already handled
                continue
            for pattern in patterns:
                if re.search(pattern, processed_message):
                    current_intent = category
                    break # Found a match, prioritize this one
            if current_intent:
                break
        
        # --- Contextual Logic (using last_user_intent / last_bot_intent) ---
        response = None

        if self.last_bot_intent == 'coping_strategy' and current_intent in ['affirmation', 'positive', 'general_support']:
            # User acknowledged or reacted positively to a suggested strategy
            response = random.choice([
                "That's great to hear! How does practicing that strategy feel for you?",
                "I'm glad that resonates. Is there anything else on your mind today?",
                "Wonderful. Remember, even small steps can make a difference."
            ])
            self.last_user_intent = current_intent # Update for next turn
            self.last_bot_intent = 'proactive_offer_support' # Proactively offer more support
            return response
        
        elif self.last_bot_intent == 'seeking_resources' and current_intent in ['yes', 'affirmation', 'general_support']:
            # User confirmed they want resources after being offered
            response = random.choice([
                "Okay, I can help with that. For immediate crisis support, remember 988 or Crisis Text Line (text HOME to 741741). For general support, consider NAMI or Mental Health America. Would you like direct links?",
                "Great! I have information on therapy, support groups, and self-help resources. What are you looking for specifically?",
                "Providing resources is important. Let me tell you about a few options: Therapy directories like Psychology Today, or online support communities like 7 Cups. Which sounds more helpful?"
            ])
            self.last_user_intent = current_intent
            self.last_bot_intent = 'providing_resources_detail'
            return response

        elif self.last_user_intent == 'gratitude' and current_intent == 'gratitude':
            # Handle repeated thanks gracefully
            response = random.choice(self.supportive_responses['gratitude'])
            self.last_user_intent = current_intent # Update intent
            self.last_bot_intent = 'gratitude' # Bot still thanks
            return response
        
        elif current_intent == 'gratitude': # If user says thank you
            response = random.choice(self.supportive_responses['gratitude'])
            self.last_user_intent = current_intent
            self.last_bot_intent = 'gratitude'
            return response
        
        elif current_intent == 'goodbye': # If user says goodbye
            response = random.choice(self.supportive_responses['goodbye'])
            self.last_user_intent = current_intent
            self.last_bot_intent = 'goodbye'
            return response
        
        # --- Main Intent-based Response (if no specific contextual rule applied) ---
        if current_intent:
            response = random.choice(self.supportive_responses.get(current_intent, self.supportive_responses['general_support']))
            self.last_user_intent = current_intent # Store the recognized intent
            self.last_bot_intent = current_intent # Bot's response aligns with user intent
            return response

        # --- Sentiment-based Fallback (if no specific pattern matched) ---
        if sentiment < -0.4: 
            self.last_user_intent = 'negative_sentiment' # Track general sentiment intent
            self.last_bot_intent = 'general_support'
            return random.choice(self.supportive_responses['depression'] + 
                                 self.supportive_responses['anxiety'] + 
                                 self.supportive_responses['stress'] +
                                 self.supportive_responses['general_support'])
        elif sentiment > 0.4: 
            self.last_user_intent = 'positive_sentiment'
            self.last_bot_intent = 'positive'
            return random.choice(self.supportive_responses['positive'])
        elif sentiment >= -0.2 and sentiment <= 0.2: # Neutral or slightly neutral
            self.last_user_intent = 'neutral_inquiry'
            self.last_bot_intent = 'neutral_inquiry'
            return random.choice(self.supportive_responses['neutral_inquiry'])
        
        # --- Ultimate Fallback (if nothing else matches) ---
        self.last_user_intent = 'uncertain'
        self.last_bot_intent = 'uncertain'
        return random.choice(self.supportive_responses['general_support'] + self.supportive_responses['uncertain'])


    def generate_response(self, user_message, conversation_history=None):
        """Generate appropriate response based on user input"""
        
        # Increment turn count (for potential future use, e.g., long-term memory)
        self.turn_count += 1

        if self.detect_crisis(user_message):
            self.last_user_intent = 'crisis' # Set user intent
            return self.get_crisis_response()
        
        try:
            if openai.api_key:
                logger.info("Using OpenAI API for response generation.")
                messages_for_api = [
                    {
                        "role": "system",
                        "content": """You are a compassionate and empathetic mental health support chatbot. 
                        Your primary goal is to listen, provide non-judgmental support, and encourage users to seek professional help when appropriate. 
                        You MUST NOT provide medical diagnosis, direct treatment advice, or claim to be a licensed therapist.
                        Focus on validating feelings, offering coping strategies, and suggesting reputable resources.
                        Keep responses concise but helpful. Always prioritize safety and well-being.
                        If the user expresses positive feelings, reinforce them.
                        Maintain a warm, understanding, and encouraging tone."""
                    }
                ]
                
                if conversation_history:
                    for msg in conversation_history:
                        messages_for_api.append(msg)
                
                messages_for_api.append({"role": "user", "content": user_message})

                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo", 
                    messages=messages_for_api,
                    max_tokens=250, 
                    temperature=0.7, 
                    top_p=0.9 
                )
                
                bot_response = response.choices[0].message.content.strip()
                sentiment = self.analyze_sentiment(user_message) 
                
                # Update last intents even with OpenAI for consistency (if you switch back)
                # This requires parsing OpenAI's response to infer intent, which is hard.
                # For simplicity, if OpenAI is used, the rule-based context won't be as precise.
                self.last_user_intent = None # Reset or infer from GPT response if possible
                self.last_bot_intent = None 
                
                return {
                    'message': bot_response,
                    'is_crisis': False,
                    'sentiment': sentiment
                }
            else:
                logger.warning("OPENAI_API_KEY not found. Falling back to rule-based responses.")
                sentiment = self.analyze_sentiment(user_message)
                bot_response = self._get_rule_based_response(user_message, sentiment, conversation_history)
                return {
                    'message': bot_response,
                    'is_crisis': False,
                    'sentiment': sentiment
                }
        except openai.AuthenticationError: 
            logger.error("OpenAI API Authentication Error: Your API key is invalid, revoked, or expired. Falling back to rule-based.")
            sentiment = self.analyze_sentiment(user_message)
            bot_response = self._get_rule_based_response(user_message, sentiment, conversation_history)
            return {
                'message': bot_response,
                'is_crisis': False,
                'sentiment': sentiment,
                'warning': "API key invalid, using fallback responses."
            }
        except openai.APIError as e: 
            logger.error(f"OpenAI API Error: {e}. Falling back to rule-based.")
            sentiment = self.analyze_message(user_message) # Corrected typo from analyze_sentiment
            bot_response = self._get_rule_based_response(user_message, sentiment, conversation_history)
            return {
                'message': bot_response,
                'is_crisis': False,
                'sentiment': sentiment,
                'warning': "API error, using fallback responses."
            }
        except Exception as e:
            logger.error(f"Unexpected error in generate_response: {e}", exc_info=True) 
            sentiment = self.analyze_sentiment(user_message) 
            return {
                'message': "I'm here to listen. Can you tell me more about how you're feeling?",
                'is_crisis': False,
                'sentiment': sentiment,
                'error': str(e)
            }