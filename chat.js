/**
 * Mental Health Chatbot - Complete JavaScript Implementation
 * Handles chat functionality, mood tracking, and user interactions
 *
 * Improvised to address double-triggering and empty message flashes.
 */

class MentalHealthChatbot {
    constructor() {
        // Chat elements
        this.messageInput = document.getElementById('message-input');
        this.chatMessages = document.getElementById('chat-messages');
        this.sendButton = document.getElementById('send-button');
        this.typingIndicator = document.getElementById('typing-indicator');
        
        // State management
        this.isProcessing = false;
        this.messageHistory = [];
        this.currentConversationId = null;
        
        // Configuration
        this.config = {
            maxMessageLength: 500,
            typingDelay: 1000,          // Delay before bot's response appears
            clearInputDelay: 100,       // Small delay before clearing input to prevent race conditions
            autoScrollOffset: 100,
            retryAttempts: 3
        };
        
        this.init();
    }
    
    /**
     * Initialize the chatbot
     */
    init() {
        this.setupEventListeners();
        this.loadChatHistory(); // Placeholder for loading old messages
        this.focusInput();
        this.setupKeyboardShortcuts();
        this.initializeAutoResize();
        
        // Set initial state
        this.updateSendButtonState();
        this.scrollToBottom();
        
        console.log('Mental Health Chatbot initialized successfully');
    }
    
    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => this.handleKeyPress(e));
            this.messageInput.addEventListener('input', () => this.handleInput());
            this.messageInput.addEventListener('paste', (e) => this.handlePaste(e));
            this.messageInput.addEventListener('focus', () => this.handleInputFocus());
            this.messageInput.addEventListener('blur', () => this.handleInputBlur());
        }
        
        if (this.sendButton) {
            // Ensure type="button" in HTML is used to prevent default form submission
            this.sendButton.addEventListener('click', (e) => {
                e.preventDefault(); // Explicitly prevent default behavior
                this.sendMessage();
            });
        }
        
        window.addEventListener('beforeunload', () => this.handleBeforeUnload());
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        if (this.chatMessages) {
            this.chatMessages.addEventListener('scroll', () => this.handleScroll());
        }
    }
    
    /**
     * Handle keyboard input
     */
    handleKeyPress(event) {
        if (event.key === 'Enter') {
            if (event.shiftKey) {
                // Allow line break with Shift+Enter
                return;
            } else {
                // Send message with Enter
                event.preventDefault(); // Prevent default form submission
                this.sendMessage();
            }
        }
    }
    
    /**
     * Handle input field changes
     */
    handleInput() {
        this.updateSendButtonState();
        this.updateCharacterCount();
        this.autoResizeTextarea();
        this.handleTypingIndicator(); // For future real-time typing indicators
    }
    
    /**
     * Handle paste events
     */
    handlePaste(event) {
        setTimeout(() => {
            this.enforceMaxLength();
            this.updateCharacterCount();
        }, 0);
    }
    
    /**
     * Handle input focus
     */
    handleInputFocus() {
        this.markConversationActive(); // For future active session tracking
    }
    
    /**
     * Handle input blur
     */
    handleInputBlur() {
        this.clearTypingIndicator(); // Clear local typing indicator
    }
    
    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
            
            if (e.key === 'Escape' && document.activeElement === this.messageInput) {
                this.clearInput();
            }
            
            if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                e.preventDefault();
                this.focusInput();
            }
        });
    }
    
    /**
     * Send message to the chatbot
     */
    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        // --- Validation ---
        if (this.isProcessing) {
            // If already processing, exit immediately to prevent queueing or double-sending
            // this.showTemporaryError('Please wait for the previous message to process'); // Can be too noisy
            return;
        }

        if (!message) {
            this.showTemporaryError('Please enter a message.');
            return;
        }
        
        if (message.length > this.config.maxMessageLength) {
            this.showTemporaryError(`Message too long. Maximum ${this.config.maxMessageLength} characters.`);
            return;
        }
        
        if (!navigator.onLine) {
            this.showTemporaryError('No internet connection. Please check your network.');
            return;
        }
        // --- End Validation ---
        
        try {
            this.setProcessingState(true); // Disable input and button
            
            this.addMessageToChat('You', message, 'user-message', new Date());
            
            // Clear input after a small delay to allow `isProcessing` to prevent re-entry
            setTimeout(() => {
                this.clearInput(); 
            }, this.config.clearInputDelay);
            
            this.showTypingIndicator();
            
            const response = await this.sendMessageWithRetry(message);
            
            await this.handleBotResponse(response);
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.handleError(error);
        } finally {
            this.setProcessingState(false); // Re-enable input and button
            this.hideTypingIndicator();
        }
    }
    
    /**
     * Send message with retry logic
     */
    async sendMessageWithRetry(message, attempt = 1) {
        try {
            const response = await fetch('/process-message/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCookie('csrftoken'), // Include CSRF token
                },
                body: JSON.stringify({ 
                    message: message,
                    conversation_id: this.currentConversationId 
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`HTTP ${response.status}: ${errorData.error || response.statusText}`);
            }
            
            const data = await response.json();
            return data;
            
        } catch (error) {
            if (attempt < this.config.retryAttempts) {
                console.warn(`Retry attempt ${attempt} failed for message: "${message}". Error: ${error.message}. Retrying...`);
                await this.delay(1000 * attempt); // Progressive delay
                return this.sendMessageWithRetry(message, attempt + 1);
            }
            throw error; // Re-throw after final attempt
        }
    }
    
    /**
     * Handle bot response
     */
    async handleBotResponse(data) {
        if (data.error) {
            throw new Error(data.error);
        }
        
        if (data.bot_response) {
            await this.delay(this.config.typingDelay); // Add small delay for natural feel
            
            const messageClass = data.is_crisis ? 'crisis-message' : 'bot-message';
            this.addMessageToChat('Support Bot', data.bot_response, messageClass, new Date());
            
            if (data.is_crisis) {
                this.handleCrisisResponse(data);
            }
            
            if (data.sentiment !== undefined) {
                this.handleSentimentFeedback(data.sentiment);
            }
            
            if (data.conversation_id) {
                this.currentConversationId = data.conversation_id;
            }
            
            this.messageHistory.push({
                user: data.user_message || '',
                bot: data.bot_response,
                timestamp: new Date(),
                sentiment: data.sentiment,
                is_crisis: data.is_crisis
            });
            
            this.autoSaveConversation(); // Placeholder for saving state
        }
    }
    
    /**
     * Handle crisis response
     */
    handleCrisisResponse(data) {
        if (data.support_resources && data.support_resources.length > 0) {
            setTimeout(() => {
                this.showCrisisModal(data.support_resources);
            }, 500);
        }
        this.addSystemMessage('⚠️ Crisis support resources have been provided. If this is an emergency, please call 911 immediately.');
        this.logCrisisEvent(data); // Log for backend monitoring
    }
    
    /**
     * Handle sentiment feedback
     */
    handleSentimentFeedback(sentiment) {
        if (sentiment < -0.5) {
            this.addSystemMessage('💙 I notice you might be going through a difficult time. Remember that support is available.');
        } else if (sentiment > 0.5) {
            this.addSystemMessage('😊 It\'s wonderful to hear some positivity in your message!');
        }
    }
    
    /**
     * Add message to chat interface
     */
    addMessageToChat(sender, content, className, timestamp) {
        if (!this.chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${className}`;
        messageDiv.setAttribute('data-timestamp', timestamp.toISOString());
        
        const timeString = timestamp.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const icon = sender === 'You' ? 'fas fa-user' : 'fas fa-robot';
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <div class="message-header">
                    <strong><i class="${icon}"></i> ${sender}</strong>
                    <span class="message-time">${timeString}</span>
                </div>
                <div class="message-text">${this.formatMessageContent(content)}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.animateMessageIn(messageDiv);
        this.scrollToBottom();
        this.updateAriaLive(content); // For screen readers
    }
    
    /**
     * Add system message
     */
    addSystemMessage(content) {
        this.addMessageToChat('System', content, 'system-message', new Date());
    }
    
    /**
     * Format message content
     */
    formatMessageContent(content) {
        let formatted = content.replace(/\n/g, '<br>'); // Convert line breaks
        formatted = this.linkifyUrls(formatted);         // Make URLs clickable
        formatted = this.linkifyPhoneNumbers(formatted); // Make phone numbers clickable
        formatted = this.sanitizeHtml(formatted);        // Basic HTML sanitization
        return formatted;
    }
    
    /**
     * Make URLs clickable
     */
    linkifyUrls(text) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        return text.replace(urlRegex, '<a href="\$1" target="_blank" rel="noopener noreferrer">\$1</a>');
    }
    
    /**
     * Make phone numbers clickable
     */
    linkifyPhoneNumbers(text) {
        const phoneRegex = /(\b\d{3}[-.]?\d{3}[-.]?\d{4}\b)/g;
        return text.replace(phoneRegex, '<a href="tel:\$1">\$1</a>');
    }
    
    /**
     * Basic HTML sanitization
     */
    sanitizeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html; // Escapes HTML characters
        return div.innerHTML;
    }
    
    /**
     * Animate message in
     */
    animateMessageIn(messageElement) {
        messageElement.style.opacity = '0';
        messageElement.style.transform = 'translateY(20px)';
        requestAnimationFrame(() => {
            messageElement.style.transition = 'all 0.3s ease-out';
            messageElement.style.opacity = '1';
            messageElement.style.transform = 'translateY(0)';
        });
    }
    
    /**
     * Show typing indicator
     */
    showTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'block';
            this.scrollToBottom();
        }
    }
    
    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = 'none';
        }
    }
    
    /**
     * Show crisis modal
     */
    showCrisisModal(resources) {
        const modal = document.getElementById('crisisModal');
        const resourcesDiv = document.getElementById('crisis-resources');
        if (!modal || !resourcesDiv) return;
        
        let resourcesHtml = `
            <div class="alert alert-danger mb-4">
                <div class="d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle fa-2x me-3"></i>
                    <div>
                        <h6 class="alert-heading mb-1">Immediate Support Available</h6>
                        <p class="mb-0">Your safety is important. Please consider reaching out to these resources immediately:</p>
                    </div>
                </div>
            </div>
        `;
        resources.forEach(resource => {
            resourcesHtml += `
                <div class="card mb-3 border-danger">
                    <div class="card-body">
                        <h6 class="card-title text-danger">
                            <i class="fas fa-life-ring"></i> ${resource.title}
                        </h6>
                        <p class="card-text">${resource.description}</p>
                        <div class="d-flex gap-2 flex-wrap">
                            ${resource.phone_number ? `
                                <a href="tel:${resource.phone_number}" class="btn btn-danger btn-sm">
                                    <i class="fas fa-phone"></i> Call ${resource.phone_number}
                                </a>
                            ` : ''}
                            ${resource.url ? `
                                <a href="${resource.url}" target="_blank" class="btn btn-outline-danger btn-sm">
                                    <i class="fas fa-external-link-alt"></i> Visit Website
                                </a>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        });
        resourcesDiv.innerHTML = resourcesHtml;
        const bootstrapModal = new bootstrap.Modal(modal);
        bootstrapModal.show();
        setTimeout(() => {
            const firstCallButton = modal.querySelector('a[href^="tel:"]');
            if (firstCallButton) {
                firstCallButton.focus();
            }
        }, 500);
    }
    
    /**
     * Set processing state (disable/enable input and button)
     */
    setProcessingState(processing) {
        this.isProcessing = processing;
        if (this.messageInput) {
            this.messageInput.disabled = processing;
        }
        if (this.sendButton) {
            this.sendButton.disabled = processing;
            this.sendButton.innerHTML = processing 
                ? '<i class="fas fa-spinner fa-spin"></i> Sending...'
                : '<i class="fas fa-paper-plane"></i> Send';
        }
        if (!processing) {
            this.focusInput();
        }
    }
    
    /**
     * Update send button state based on input and processing status
     */
    updateSendButtonState() {
        if (!this.sendButton || !this.messageInput) return;
        const hasMessage = this.messageInput.value.trim().length > 0;
        this.sendButton.disabled = !hasMessage || this.isProcessing;
    }
    
    /**
     * Update character count display for message input
     */
    updateCharacterCount() {
        const charCountElement = document.getElementById('char-count'); 
        if (charCountElement && this.messageInput) {
            const currentLength = this.messageInput.value.length;
            const maxLength = this.config.maxMessageLength;
            charCountElement.textContent = `${currentLength}/${maxLength}`;
            if (currentLength > maxLength * 0.9) {
                charCountElement.className = 'text-danger';
            } else if (currentLength > maxLength * 0.75) {
                charCountElement.className = 'text-warning';
            } else {
                charCountElement.className = 'text-muted';
            }
        }
    }
    
    /**
     * Auto-resize textarea based on content
     */
    autoResizeTextarea() {
        if (this.messageInput) {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
        }
    }
    
    /**
     * Initialize auto-resize when page loads
     */
    initializeAutoResize() {
        if (this.messageInput) {
            this.autoResizeTextarea();
        }
    }
    
    /**
     * Enforce maximum length on input
     */
    enforceMaxLength() {
        if (this.messageInput && this.messageInput.value.length > this.config.maxMessageLength) {
            this.messageInput.value = this.messageInput.value.substring(0, this.config.maxMessageLength);
            this.showTemporaryError(`Message truncated to ${this.config.maxMessageLength} characters.`);
        }
    }
    
    /**
     * Clear input field and related states
     */
    clearInput() {
        if (this.messageInput) {
            this.messageInput.value = '';
            this.autoResizeTextarea();
            this.updateSendButtonState();
            this.updateCharacterCount();
        }
    }
    
    /**
     * Focus input field unless currently processing
     */
    focusInput() {
        if (this.messageInput && !this.isProcessing) {
            this.messageInput.focus();
        }
    }
    
    /**
     * Scroll to bottom of chat messages area
     */
    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }
    
    /**
     * Handle scroll events (placeholder for future features like lazy loading)
     */
    handleScroll() {
        // Implement features like loading more messages or "new message" indicator
    }
    
    /**
     * Show temporary notification/error message on the side
     */
    showTemporaryError(message, duration = 3000) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        errorDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
        errorDiv.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, duration);
    }
    
    /**
     * Handle fetch and other errors gracefully
     */
    handleError(error) {
        let errorMessage = 'Sorry, I encountered an error. Please try again.';
        if (error.message.includes('HTTP')) {
            errorMessage = `Server error: ${error.message}. Please try again.`;
        } else if (error.message.includes('fetch')) {
            errorMessage = 'Network error. Please check your connection and try again.';
        } else if (error.message.includes('timeout')) {
            errorMessage = 'Request timed out. Please try again.';
        } else if (error.message.includes('500')) {
            errorMessage = 'Internal server error. Please try again in a moment.';
        }
        this.addMessageToChat('System', `❌ ${errorMessage}`, 'system-message error-message', new Date());
    }
    
    /**
     * Handle network status changes
     */
    handleOnline() {
        this.addSystemMessage('🟢 Connection restored.');
    }
    handleOffline() {
        this.addSystemMessage('🔴 No internet connection. Messages will be sent when connection is restored.');
    }
    
    /**
     * Handle page unload (e.g., save conversation state)
     */
    handleBeforeUnload() {
        this.saveConversationState(); 
    }
    
    /**
     * Load chat history from backend/localStorage (placeholder)
     */
    loadChatHistory() {
        console.log('Loading chat history...');
    }
    
    /**
     * Auto-save conversation state (placeholder)
     */
    autoSaveConversation() {
        // console.log('Auto-saving conversation...'); // Can be noisy
    }
    
    /**
     * Save conversation state explicitly (placeholder)
     */
    saveConversationState() {
        const state = {
            messageHistory: this.messageHistory,
            conversationId: this.currentConversationId,
            timestamp: new Date().toISOString()
        };
        try {
            localStorage.setItem('chatbot_conversation_state', JSON.stringify(state));
        } catch (error) {
            console.warn('Could not save conversation state to localStorage:', error);
        }
    }
    
    /**
     * Utility: Create delay for better UX
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Get CSRF token from cookies
     */
    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    /**
     * Update ARIA live region for screen readers (accessibility)
     */
    updateAriaLive(content) {
        const ariaLive = document.getElementById('aria-live-region');
        if (ariaLive) {
            ariaLive.textContent = content;
        }
    }
    
    /**
     * Handle typing indicator logic (for future real-time features)
     */
    handleTypingIndicator() {
        // Implement logic for showing/hiding typing indicators to other users/sessions
    }
    
    /**
     * Clear typing indicator (if any, for single user)
     */
    clearTypingIndicator() {
        // Implement logic for clearing local typing indicators
    }
    
    /**
     * Mark conversation as active (for backend tracking)
     */
    markConversationActive() {
        // Send a ping to backend to mark conversation as active/last used
    }
    
    /**
     * Log crisis event for backend monitoring
     */
    logCrisisEvent(data) {
        console.warn('Crisis event detected:', {
            timestamp: new Date().toISOString(),
            conversationId: this.currentConversationId,
            sentiment: data.sentiment,
            triggeredMessage: data.user_message 
        });
        // Here you might send an AJAX call to a specific backend endpoint
        // to log the crisis event and potentially notify an administrator.
    }
}

// Utility functions exposed globally for HTML onclick (Clear Chat, Export, Print)
const ChatUtils = {
    clearChat() {
        if (confirm('Are you sure you want to clear this chat? This action cannot be undone.')) {
            window.location.href = '/clear-chat/';
        }
    },
    exportChat() {
        const messages = document.querySelectorAll('.message');
        let chatText = 'Mental Health Chat Export\n';
        chatText += '='.repeat(50) + '\n\n';
        
        messages.forEach(message => {
            const sender = message.querySelector('strong').textContent;
            const content = message.querySelector('.message-text').textContent;
            const time = message.querySelector('.message-time').textContent;
            
            chatText += `[${time}] ${sender}\n${content}\n\n`;
        });
        
        const blob = new Blob([chatText], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mental-health-chat-${new Date().toISOString().split('T')[0]}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },
    printChat() {
        window.print();
    }
};

// Global variables to make instances accessible if needed (though not strictly required for this project)
let chatbotInstance;

// Global functions for onclick handlers (used in chat.html)
function clearChat() { ChatUtils.clearChat(); }
function exportChat() { ChatUtils.exportChat(); }
function printChat() { ChatUtils.printChat(); }
function sendMessage() { 
    if (chatbotInstance) {
        chatbotInstance.sendMessage();
    }
}

// Initialize chatbot when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize chatbot on chat page
    if (document.getElementById('chat-messages')) {
        chatbotInstance = new MentalHealthChatbot();
        console.log('Mental Health Chatbot loaded successfully');
    }
    
    // Add ARIA live region for screen readers (hidden but read aloud)
    if (!document.getElementById('aria-live-region')) {
        const ariaDiv = document.createElement('div');
        ariaDiv.id = 'aria-live-region';
        ariaDiv.className = 'sr-only'; 
        ariaDiv.setAttribute('aria-live', 'polite'); 
        ariaDiv.setAttribute('aria-atomic', 'true'); 
        document.body.appendChild(ariaDiv);
    }
    
    // Add keyboard navigation hints for accessibility (screen reader only)
    const helpText = document.createElement('div');
    helpText.className = 'sr-only';
    helpText.innerHTML = 'Press Ctrl+Enter to send message. Press Escape to clear input. Press Ctrl+/ to focus input.';
    document.body.appendChild(helpText);
});