/**
 * Mood Tracker JavaScript
 * Handles mood selection, form submission, and statistics
 */

class MoodTracker {
    constructor() {
        this.selectedMood = null;
        this.moodForm = document.getElementById('mood-form');
        this.submitButton = document.getElementById('submit-mood');
        this.notesTextarea = document.getElementById('notes');
        this.charCount = document.getElementById('char-count');
        this.moodOptions = document.querySelectorAll('.mood-option');
        // Reads from data-post-url on the form.
        // The HTML now explicitly provides data-post-url="/mood-tracker/", bypassing template tag issues.
        this.postUrl = this.moodForm ? this.moodForm.dataset.postUrl : '/mood-tracker/'; 

        // Configuration
        this.config = {
            maxNotesLength: 500,
            animationDelay: 100,
            feedbackDuration: 3000
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.generateMoodStats();
        this.initializeAnimations();
        this.updateCharCount();

        console.log('Mood Tracker initialized');
        console.log('MoodTracker postUrl:', this.postUrl); 
    }

    setupEventListeners() {
        // Character counter for notes
        if (this.notesTextarea && this.charCount) {
            this.notesTextarea.addEventListener('input', () => this.updateCharCount());
            this.notesTextarea.addEventListener('keydown', (e) => this.handleNotesKeydown(e));
        }

        // Form submission
        if (this.moodForm) {
            this.moodForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Mood option click events: Use event delegation or attach directly
        this.moodOptions.forEach(option => {
            // Remove onclick from HTML, attach event listener here
            option.addEventListener('click', () => this.selectMood(parseInt(option.dataset.mood))); 
            option.addEventListener('mouseenter', () => this.handleMoodHover(option));
            option.addEventListener('mouseleave', () => this.handleMoodLeave(option));
        });

        // Keyboard navigation for mood options
        this.setupKeyboardNavigation();
    }

    setupKeyboardNavigation() {
        this.moodOptions.forEach((option, index) => {
            option.setAttribute('tabindex', '0'); 
            option.setAttribute('role', 'radio'); 
            option.setAttribute('aria-checked', 'false'); 

            option.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.selectMood(parseInt(option.dataset.mood));
                } else if (e.key === 'ArrowLeft' && index > 0) {
                    e.preventDefault();
                    this.moodOptions[index - 1].focus();
                } else if (e.key === 'ArrowRight' && index < this.moodOptions.length - 1) {
                    e.preventDefault();
                    this.moodOptions[index + 1].focus();
                }
            });
        });
    }

    handleNotesKeydown(e) {
        // Allow Ctrl+Enter to submit form
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            if (this.selectedMood) {
                this.handleFormSubmit(e);
            }
        }
    }

    updateCharCount() {
        if (!this.notesTextarea || !this.charCount) return;

        const currentLength = this.notesTextarea.value.length;
        const maxLength = this.config.maxNotesLength;

        this.charCount.textContent = currentLength;

        // Update styling based on character count
        this.charCount.className = '';
        if (currentLength > maxLength * 0.9) {
            this.charCount.classList.add('text-danger');
        } else if (currentLength > maxLength * 0.75) {
            this.charCount.classList.add('text-warning');
        } else {
            this.charCount.classList.add('text-muted');
        }

        // Prevent exceeding max length
        if (currentLength > maxLength) {
            this.notesTextarea.value = this.notesTextarea.value.substring(0, maxLength);
            this.showFeedback('Maximum character limit reached', 'warning');
        }
    }

    selectMood(level) {
        // Remove previous selection
        this.moodOptions.forEach(option => {
            option.classList.remove('selected');
            option.setAttribute('aria-checked', 'false');
        });

        // Add selection to clicked option
        const selectedOption = document.querySelector(`[data-mood="${level}"]`);
        if (selectedOption) {
            selectedOption.classList.add('selected');
            selectedOption.setAttribute('aria-checked', 'true');
            selectedOption.focus(); 
        }

        // Set hidden input value
        document.getElementById('mood_level').value = level;
        this.selectedMood = level;

        // Enable submit button
        if (this.submitButton) {
            this.submitButton.disabled = false;
        }

        // Provide immediate visual/auditory feedback (for accessibility)
        this.showFeedback(`Selected mood: ${this.getMoodLabel(level)}`, 'info');
    }

    handleMoodHover(option) {
        // Add subtle hover animation or feedback if needed
    }

    handleMoodLeave(option) {
        // Remove hover feedback
    }

    getMoodLabel(level) {
        const labels = {
            1: 'Very Sad',
            2: 'Sad',
            3: 'Neutral',
            4: 'Happy',
            5: 'Very Happy'
        };
        return labels[level] || '';
    }

    async handleFormSubmit(e) {
        e.preventDefault();

        if (!this.selectedMood) {
            this.showError('Please select your mood level first.');
            return;
        }

        // Disable button during submission
        this.setSubmitButtonState(false, 'Saving...');

        try {
            const formData = new FormData(this.moodForm);

            // Log the URL just before fetch
            console.log('Fetching mood data to URL:', this.postUrl); 

            const response = await fetch(this.postUrl, { 
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken')
                }
            });

            // Check if response is OK (200-299 status) before trying to parse JSON
            if (!response.ok) {
                const errorText = await response.text(); 
                console.error('Server response not OK:', response.status, response.statusText, errorText);
                if (errorText.startsWith('<!DOCTYPE html>')) {
                    this.showError('Server returned an HTML error page. Check Django logs for details.');
                } else {
                    this.showError(`Server error (${response.status}): ${errorText || response.statusText}`);
                }
                return; 
            }

            const data = await response.json();

            if (data.status === 'success') {
                this.showSuccessModal();
            } else {
                this.showError(data.error || 'An error occurred while saving your mood.');
            }
        } catch (error) {
            console.error('Error submitting mood:', error);
            // More specific error message for JSON parsing failures
            if (error instanceof SyntaxError) {
                this.showError('Could not process server response. Expected JSON, got invalid data.');
            } else {
                this.showError('Network error. Please check your connection and try again.');
            }
        } finally {
            this.setSubmitButtonState(true, 'Save Mood Entry');
        }
    }

    setSubmitButtonState(enabled, text) {
        if (this.submitButton) {
            this.submitButton.disabled = !enabled;
            this.submitButton.innerHTML = enabled 
                ? `<i class="fas fa-save"></i> ${text}`
                : `<i class="fas fa-spinner fa-spin"></i> ${text}`;
        }
    }

    showSuccessModal() {
        const modal = new bootstrap.Modal(document.getElementById('successModal'));
        modal.show();
    }

    showError(message) {
        document.getElementById('error-message').textContent = message;
        const modal = new bootstrap.Modal(document.getElementById('errorModal'));
        modal.show();
    }

    resetForm() {
        // Reset form
        this.moodForm.reset();
        this.selectedMood = null;

        // Remove selections
        this.moodOptions.forEach(option => {
            option.classList.remove('selected');
            option.setAttribute('aria-checked', 'false');
        });

        // Disable submit button
        if (this.submitButton) {
            this.submitButton.disabled = true;
        }

        // Reset character count
        this.updateCharCount();

        // Focus on the first mood option for accessibility after reset
        if (this.moodOptions.length > 0) {
            this.moodOptions[0].focus();
        }

        // Re-generate mood stats in case new entry needs to be reflected
        this.generateMoodStats();
    }

    generateMoodStats() {
        const statsContainer = document.getElementById('mood-stats');
        if (!statsContainer) return;

        const moodEntries = document.querySelectorAll('.mood-entry');
        if (moodEntries.length === 0) {
            statsContainer.innerHTML = `
                <div class="col-12 text-center text-muted py-4">
                    <i class="fas fa-chart-line fa-3x mb-3 opacity-50"></i>
                    <h6>No mood data to display yet.</h6>
                    <p class="small">Submit your first mood entry to see your statistics here!</p>
                </div>
            `;
            return;
        }

        const stats = this.calculateStats(moodEntries);
        this.renderStats(statsContainer, stats);
    }

    calculateStats(entries) {
        const moods = Array.from(entries).map(entry => {
            const classList = Array.from(entry.classList);
            const moodClass = classList.find(cls => cls.startsWith('mood-'));
            return parseInt(moodClass?.split('-')[1] || 0);
        }).filter(mood => mood > 0);

        if (moods.length === 0) return null;

        const average = moods.reduce((sum, mood) => sum + mood, 0) / moods.length;
        const mostCommon = this.getMostCommon(moods);
        const trend = this.calculateTrend(moods);

        return {
            totalEntries: moods.length,
            averageMood: average.toFixed(1),
            mostCommon: mostCommon,
            trend: trend
        };
    }

    getMostCommon(arr) {
        const counts = {};
        let maxCount = 0;
        let mostCommon = [];

        arr.forEach(item => {
            counts[item] = (counts[item] || 0) + 1;
            if (counts[item] > maxCount) {
                maxCount = counts[item];
                mostCommon = [item];
            } else if (counts[item] === maxCount) {
                mostCommon.push(item);
            }
        });

        // Return a single value or handle multiple common moods as needed
        return mostCommon.length === 1 ? mostCommon[0] : mostCommon[0]; // Simplification for display
    }

    calculateTrend(moods) {
        if (moods.length < 2) return 'stable';

        // Use a simple moving average for trend over the last few entries
        const trendWindow = Math.min(moods.length, 5); // Look at last 5 entries or fewer if not enough
        const recentMoods = moods.slice(-trendWindow);
        const earlierMoods = moods.slice(0, trendWindow);

        const recentAvg = recentMoods.reduce((sum, mood) => sum + mood, 0) / recentMoods.length;
        const earlierAvg = earlierMoods.reduce((sum, mood) => sum + mood, 0) / earlierMoods.length;

        const threshold = 0.3; // Define a threshold for significant change

        if (recentAvg > earlierAvg + threshold) return 'improving';
        if (recentAvg < earlierAvg - threshold) return 'declining';
        return 'stable';
    }

    renderStats(container, stats) {
        if (!stats) {
            container.innerHTML = '<p class="text-muted text-center py-4">No sufficient data for statistics.</p>';
            return;
        }

        const trendIcons = {
            'improving': { icon: 'fa-arrow-up', color: 'text-success' },
            'declining': { icon: 'fa-arrow-down', color: 'text-danger' },
            'stable': { icon: 'fa-minus', color: 'text-info' }
        };

        const trendInfo = trendIcons[stats.trend];

        container.innerHTML = `
            <div class="col-md-3 col-6 mb-3">
                <div class="stat-card">
                    <div class="stat-number text-primary">${stats.totalEntries}</div>
                    <div class="small text-muted">Total Entries</div>
                </div>
            </div>
            <div class="col-md-3 col-6 mb-3">
                <div class="stat-card">
                    <div class="stat-number text-info">${stats.averageMood}</div>
                    <div class="small text-muted">Average Mood (1-5)</div>
                </div>
            </div>
            <div class="col-md-3 col-6 mb-3">
                <div class="stat-card">
                    <div class="stat-number text-success">${this.getMoodLabel(stats.mostCommon)}</div>
                    <div class="small text-muted">Most Common Mood</div>
                </div>
            </div>
            <div class="col-md-3 col-6 mb-3">
                <div class="stat-card">
                    <div class="stat-number ${trendInfo.color}">
                        <i class="fas ${trendInfo.icon}"></i>
                    </div>
                    <div class="small text-muted">${stats.trend.charAt(0).toUpperCase() + stats.trend.slice(1)} Trend</div>
                </div>
            </div>
        `;
    }

    initializeAnimations() {
        // Fade in mood options on load
        this.moodOptions.forEach((option, index) => {
            option.style.opacity = '0';
            option.style.transform = 'translateY(20px)';
            setTimeout(() => {
                option.style.transition = 'all 0.5s ease-out';
                option.style.opacity = '1';
                option.style.transform = 'translateY(0)';
            }, index * this.config.animationDelay);
        });
    }

    showFeedback(message, type = 'info', duration = this.config.feedbackDuration) {
        const feedbackArea = document.getElementById('feedback-area'); // You might need to add this div in your HTML
        if (!feedbackArea) {
            console.log(`Feedback: [${type.toUpperCase()}] ${message}`);
            return;
        }

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;

        feedbackArea.appendChild(alertDiv);

        setTimeout(() => {
            bootstrap.Alert.getInstance(alertDiv)?.close();
        }, duration);
    }

    // Add getCookie method as it's used in handleFormSubmit
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

    // Get CSRF token from meta tag or cookie
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) {
            return token.value;
        }
        // Fallback to cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return null;
    }

    async handleKeyPress(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            await this.handleFormSubmit(event);
        }
    }
}

// Global function to delete mood entry
async function deleteMoodEntry(moodId) {
    if (!confirm('Are you sure you want to delete this mood entry? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/mood-tracker/delete/${moodId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': moodTrackerInstance.getCookie('csrftoken')
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.status === 'success') {
            // Remove the mood entry from the DOM
            const moodEntryElement = document.getElementById(`mood-entry-${moodId}`);
            if (moodEntryElement) {
                moodEntryElement.style.animation = 'fadeOut 0.3s ease-out';
                setTimeout(() => {
                    moodEntryElement.remove();
                    // Regenerate stats after deletion
                    if (moodTrackerInstance) {
                        moodTrackerInstance.generateMoodStats();
                    }
                    // Show success message
                    showDeleteSuccessMessage();
                }, 300);
            }
        } else {
            alert('Error deleting mood entry: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error deleting mood entry:', error);
        alert('Failed to delete mood entry. Please try again.');
    }
}

// Show success message for deletion
function showDeleteSuccessMessage() {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alertDiv.style.top = '20px';
    alertDiv.style.right = '20px';
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        <i class="fas fa-check-circle"></i> Mood entry deleted successfully!
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}

// Global variables for onclick handlers to ensure they are accessible from HTML
let moodTrackerInstance;

function selectMood(level) { // Global wrapper function for HTML onclick
    if (moodTrackerInstance) {
        moodTrackerInstance.selectMood(level);
    }
}

function resetForm() { // Global wrapper function for HTML onclick
    if (moodTrackerInstance) {
        moodTrackerInstance.resetForm();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('mood-form')) {
        moodTrackerInstance = new MoodTracker();
    }
});

// Global function for handling key press events
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        if (moodTrackerInstance) {
            moodTrackerInstance.handleFormSubmit(event);
        }
    }
}