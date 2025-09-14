// DOM Elements
const travelPrompt = document.getElementById('travelPrompt');
const generateBtn = document.getElementById('generateBtn');
const loadingSection = document.getElementById('loadingSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const inputSection = document.querySelector('.input-section');
const newSearchBtn = document.getElementById('newSearchBtn');
const retryBtn = document.getElementById('retryBtn');

// Summary elements
const summaryDestination = document.getElementById('summaryDestination');
const summaryDuration = document.getElementById('summaryDuration');
const summaryTravelers = document.getElementById('summaryTravelers');
const summaryInterests = document.getElementById('summaryInterests');
const itineraryContent = document.getElementById('itineraryContent');
const itinerarySections = document.getElementById('itinerarySections');
const preferenceSections = document.getElementById('preferenceSections');
const errorMessage = document.getElementById('errorMessage');

// State management
let currentPrompt = '';
let currentItinerary = '';
let currentSections = [];
let activeChatSections = new Set();
let preferencesData = [];
let userPreferences = {
    likes: [],
    dislikes: []
};

// Event Listeners
generateBtn.addEventListener('click', handleGenerateItinerary);
newSearchBtn.addEventListener('click', resetToSearch);
retryBtn.addEventListener('click', handleRetry);

// Allow Enter key to submit (with Shift+Enter for new line)
travelPrompt.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleGenerateItinerary();
    }
});

// Auto-resize textarea
travelPrompt.addEventListener('input', () => {
    travelPrompt.style.height = 'auto';
    travelPrompt.style.height = travelPrompt.scrollHeight + 'px';
});

// Example prompt functionality
function fillExample(card) {
    const exampleText = card.querySelector('p').textContent;
    travelPrompt.value = exampleText;
    travelPrompt.focus();
    
    // Auto-resize after filling
    travelPrompt.style.height = 'auto';
    travelPrompt.style.height = travelPrompt.scrollHeight + 'px';
    
    // Add visual feedback
    card.style.transform = 'scale(0.98)';
    setTimeout(() => {
        card.style.transform = '';
    }, 150);
}

// Main function to generate itinerary
async function handleGenerateItinerary() {
    const prompt = travelPrompt.value.trim();
    
    if (!prompt) {
        showError('Please describe your travel plans before generating an itinerary.');
        return;
    }
    
    if (prompt.length < 20) {
        showError('Please provide more details about your travel plans for a better itinerary.');
        return;
    }
    
    currentPrompt = prompt;
    showLoading();
    
    try {
        const response = await fetch('/generate_itinerary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: prompt })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate itinerary');
        }
        
        if (data.success) {
            showResults(data);
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
        
    } catch (error) {
        console.error('Error generating itinerary:', error);
        showError(error.message || 'Failed to generate itinerary. Please try again.');
    }
}

// Show loading state
function showLoading() {
    hideAllSections();
    loadingSection.classList.remove('hidden');
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
}

// Show results
function showResults(data) {
    hideAllSections();
    
    // Store current data
    preferencesData = data.sections || [];
    
    // Populate travel summary
    if (data.travel_info) {
        const info = data.travel_info;
        summaryDestination.textContent = info.destination || 'Not specified';
        summaryDuration.textContent = info.duration || 'Not specified';
        summaryTravelers.textContent = info.travelers || 'Not specified';
        summaryInterests.textContent = Array.isArray(info.interests) 
            ? info.interests.join(', ') 
            : (info.interests || 'Not specified');
    }
    
    // Display preference sections with examples for swiping
    if (data.sections && data.sections.length > 0) {
        displayPreferenceSections(data.sections);
        preferenceSections.classList.remove('hidden');
        itinerarySections.classList.add('hidden');
        itineraryContent.classList.add('hidden');
    } else {
        // Fallback to regular display if no sections
        preferenceSections.classList.add('hidden');
        itinerarySections.classList.add('hidden');
        itineraryContent.classList.remove('hidden');
        if (data.itinerary) {
            itineraryContent.innerHTML = formatItinerary(data.itinerary);
        }
    }
    
    resultsSection.classList.remove('hidden');
    resetGenerateButton();
}

// Show error state
function showError(message) {
    hideAllSections();
    errorMessage.textContent = message;
    errorSection.classList.remove('hidden');
    resetGenerateButton();
}

// Hide all sections
function hideAllSections() {
    loadingSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');
}

// Reset to search state
function resetToSearch() {
    hideAllSections();
    inputSection.style.display = 'block';
    travelPrompt.value = '';
    travelPrompt.focus();
    resetGenerateButton();
}

// Handle retry
function handleRetry() {
    if (currentPrompt) {
        travelPrompt.value = currentPrompt;
        handleGenerateItinerary();
    } else {
        resetToSearch();
    }
}

// Reset generate button
function resetGenerateButton() {
    generateBtn.disabled = false;
    generateBtn.innerHTML = '<i class="fas fa-magic"></i> Generate My Itinerary';
}

// Format itinerary text with better HTML structure
function formatItinerary(text) {
    // Convert markdown-like formatting to HTML
    let formatted = text
        // Convert headers
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        
        // Convert bold text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        
        // Convert bullet points
        .replace(/^- (.*$)/gm, '<li>$1</li>')
        .replace(/^\* (.*$)/gm, '<li>$1</li>')
        
        // Convert numbered lists
        .replace(/^\d+\. (.*$)/gm, '<li>$1</li>')
        
        // Convert line breaks to paragraphs
        .split('\n\n')
        .map(paragraph => {
            paragraph = paragraph.trim();
            if (!paragraph) return '';
            
            // Check if it's a list
            if (paragraph.includes('<li>')) {
                // Wrap list items in ul tags
                return '<ul>' + paragraph + '</ul>';
            }
            
            // Check if it's already a header
            if (paragraph.startsWith('<h')) {
                return paragraph;
            }
            
            // Regular paragraph
            return '<p>' + paragraph + '</p>';
        })
        .join('');
    
    // Clean up any double ul tags
    formatted = formatted.replace(/<\/ul>\s*<ul>/g, '');
    
    return formatted;
}

// Add some visual enhancements
document.addEventListener('DOMContentLoaded', () => {
    // Add smooth scrolling behavior
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Add focus to textarea on load
    travelPrompt.focus();
    
    // Add loading animation to generate button on hover
    generateBtn.addEventListener('mouseenter', () => {
        if (!generateBtn.disabled) {
            generateBtn.style.transform = 'translateY(-2px)';
        }
    });
    
    generateBtn.addEventListener('mouseleave', () => {
        if (!generateBtn.disabled) {
            generateBtn.style.transform = '';
        }
    });
});

// Display preference sections with examples for swiping
function displayPreferenceSections(sections) {
    preferenceSections.innerHTML = '';
    
    sections.forEach((section, index) => {
        const sectionElement = createPreferenceSectionElement(section, index);
        preferenceSections.appendChild(sectionElement);
    });
}

// Create preference section element
function createPreferenceSectionElement(section, index) {
    const sectionDiv = document.createElement('div');
    sectionDiv.className = 'preference-section';
    sectionDiv.dataset.sectionType = section.section_type;
    
    const iconMap = {
        'dining': 'fas fa-utensils',
        'activities': 'fas fa-star',
        'accommodation': 'fas fa-bed',
        'transportation': 'fas fa-car',
        'entertainment': 'fas fa-music'
    };
    
    const iconClass = iconMap[section.section_type] || 'fas fa-info-circle';
    
    sectionDiv.innerHTML = `
        <div class="section-header-new">
            <div class="section-title-new">
                <div class="section-icon-new ${section.section_type}">
                    <i class="${iconClass}"></i>
                </div>
                ${section.section_name}
            </div>
            <div class="section-subtitle">
                Swipe through these options to help us understand your preferences
            </div>
        </div>
        <div class="examples-grid" id="examples-${index}">
            <!-- Examples will be populated here -->
        </div>
        <div class="progress-indicator">
            <div class="progress-text">Progress: <span id="progress-${index}">0</span>/${section.examples.length} examples reviewed</div>
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill-${index}" style="width: 0%"></div>
            </div>
        </div>
    `;
    
    // Add examples to the grid
    const examplesGrid = sectionDiv.querySelector(`#examples-${index}`);
    section.examples.forEach((example, exampleIndex) => {
        const exampleElement = createExampleCard(example, index, exampleIndex);
        examplesGrid.appendChild(exampleElement);
    });
    
    return sectionDiv;
}

// Create individual example card
function createExampleCard(example, sectionIndex, exampleIndex) {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'example-card';
    cardDiv.dataset.sectionIndex = sectionIndex;
    cardDiv.dataset.exampleIndex = exampleIndex;
    
    // Create metadata HTML
    const metadataHTML = Object.entries(example.metadata || {}).map(([key, value]) => `
        <div class="metadata-item">
            <div class="metadata-label">${key.replace(/_/g, ' ')}</div>
            <div class="metadata-value">${value}</div>
        </div>
    `).join('');
    
    cardDiv.innerHTML = `
        <div class="swipe-feedback like">❤️</div>
        <div class="swipe-feedback dislike">❌</div>
        <div class="example-name">${example.name}</div>
        <div class="example-description">${example.description}</div>
        <div class="example-metadata">
            ${metadataHTML}
        </div>
        <div class="example-actions">
            <button class="swipe-btn dislike-btn" onclick="handleSwipe(${sectionIndex}, ${exampleIndex}, 'dislike')">
                <i class="fas fa-times"></i>
            </button>
            <button class="swipe-btn like-btn" onclick="handleSwipe(${sectionIndex}, ${exampleIndex}, 'like')">
                <i class="fas fa-heart"></i>
            </button>
        </div>
    `;
    
    return cardDiv;
}

// Handle swipe action (like/dislike)
function handleSwipe(sectionIndex, exampleIndex, action) {
    const card = document.querySelector(`[data-section-index="${sectionIndex}"][data-example-index="${exampleIndex}"]`);
    const section = preferencesData[sectionIndex];
    const example = section.examples[exampleIndex];
    
    // Add visual feedback
    card.classList.add(action === 'like' ? 'liked' : 'disliked');
    
    // Show feedback animation
    const feedback = card.querySelector(`.swipe-feedback.${action}`);
    feedback.style.opacity = '1';
    setTimeout(() => {
        feedback.style.opacity = '0';
    }, 800);
    
    // Store preference
    const preferenceData = {
        section_type: section.section_type,
        section_name: section.section_name,
        example: example,
        action: action,
        timestamp: new Date().toISOString()
    };
    
    if (action === 'like') {
        userPreferences.likes.push(preferenceData);
    } else {
        userPreferences.dislikes.push(preferenceData);
    }
    
    // Update progress
    updateSectionProgress(sectionIndex);
    
    // Disable the card after swiping
    card.style.pointerEvents = 'none';
    card.style.opacity = '0.7';
    
    console.log('User preferences updated:', userPreferences);
}

// Update progress indicator for a section
function updateSectionProgress(sectionIndex) {
    const section = preferencesData[sectionIndex];
    const totalExamples = section.examples.length;
    
    // Count reviewed examples (both liked and disliked)
    const reviewedCount = document.querySelectorAll(`[data-section-index="${sectionIndex}"].example-card.liked, [data-section-index="${sectionIndex}"].example-card.disliked`).length;
    
    const progressText = document.getElementById(`progress-${sectionIndex}`);
    const progressFill = document.getElementById(`progress-fill-${sectionIndex}`);
    
    if (progressText && progressFill) {
        progressText.textContent = reviewedCount;
        const percentage = (reviewedCount / totalExamples) * 100;
        progressFill.style.width = `${percentage}%`;
    }
    
    // Check if all sections are complete
    checkAllSectionsComplete();
}

// Check if all sections are complete and show next steps
function checkAllSectionsComplete() {
    const totalSections = preferencesData.length;
    let completedSections = 0;
    
    preferencesData.forEach((section, index) => {
        const totalExamples = section.examples.length;
        const reviewedCount = document.querySelectorAll(`[data-section-index="${index}"].example-card.liked, [data-section-index="${index}"].example-card.disliked`).length;
        
        if (reviewedCount === totalExamples) {
            completedSections++;
        }
    });
    
    if (completedSections === totalSections) {
        showCompletionMessage();
    }
}

// Show completion message when all preferences are collected
function showCompletionMessage() {
    const completionDiv = document.createElement('div');
    completionDiv.className = 'completion-message';
    completionDiv.innerHTML = `
        <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #48bb78, #38a169); color: white; border-radius: 15px; margin-top: 30px;">
            <h3 style="margin-bottom: 15px;"><i class="fas fa-check-circle"></i> Preferences Collected!</h3>
            <p style="margin-bottom: 20px;">Great! We've learned about your preferences. Ready to create your personalized itinerary?</p>
            <button onclick="generatePersonalizedItinerary()" style="background: white; color: #38a169; border: none; padding: 12px 25px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                <i class="fas fa-magic"></i> Generate My Personalized Itinerary
            </button>
        </div>
    `;
    
    preferenceSections.appendChild(completionDiv);
}

// Generate personalized itinerary based on collected preferences
async function generatePersonalizedItinerary() {
    // Show loading state
    const completionMessage = document.querySelector('.completion-message');
    if (completionMessage) {
        completionMessage.innerHTML = `
            <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #4299e1, #3182ce); color: white; border-radius: 15px;">
                <h3 style="margin-bottom: 15px;"><i class="fas fa-spinner fa-spin"></i> Creating Your Personalized Itinerary</h3>
                <p>Using your preferences to craft the perfect trip...</p>
            </div>
        `;
    }
    
    try {
        // Get the travel info from the current data
        const travelInfo = preferencesData.length > 0 ? 
            document.querySelector('#summaryDestination').textContent !== 'Not specified' ? {
                destination: document.querySelector('#summaryDestination').textContent,
                duration: document.querySelector('#summaryDuration').textContent,
                travelers: document.querySelector('#summaryTravelers').textContent,
                interests: document.querySelector('#summaryInterests').textContent.split(', ')
            } : {} : {};
        
        const response = await fetch('/generate_personalized_itinerary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: currentPrompt,
                travel_info: travelInfo,
                preferences: userPreferences
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to generate personalized itinerary');
        }
        
        if (data.success) {
            // Hide preference sections and show the personalized itinerary
            preferenceSections.classList.add('hidden');
            itinerarySections.classList.remove('hidden');
            itineraryContent.classList.remove('hidden');
            
            // Display the personalized itinerary
            if (data.sections && data.sections.length > 0) {
                displaySectionedItinerary(data.sections);
                itinerarySections.classList.remove('hidden');
                itineraryContent.classList.add('hidden');
            } else {
                itineraryContent.innerHTML = formatItinerary(data.itinerary);
                itineraryContent.classList.remove('hidden');
                itinerarySections.classList.add('hidden');
            }
            
            // Add a personalization banner
            const personalizationBanner = document.createElement('div');
            personalizationBanner.className = 'personalization-banner';
            personalizationBanner.innerHTML = `
                <div style="background: linear-gradient(135deg, #48bb78, #38a169); color: white; padding: 20px; border-radius: 12px; margin-bottom: 25px; text-align: center;">
                    <h3 style="margin: 0 0 10px 0;"><i class="fas fa-heart"></i> Personalized Just for You!</h3>
                    <p style="margin: 0; opacity: 0.9;">This itinerary was crafted based on your ${data.preferences_applied.likes_count} likes and ${data.preferences_applied.dislikes_count} dislikes</p>
                </div>
            `;
            
            // Insert the banner at the top of the results
            const firstChild = resultsSection.querySelector('.travel-summary') || resultsSection.firstChild;
            if (firstChild) {
                resultsSection.insertBefore(personalizationBanner, firstChild.nextSibling);
            }
            
            // Store the new itinerary data
            currentItinerary = data.itinerary;
            currentSections = data.sections || [];
            
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
        
    } catch (error) {
        console.error('Error generating personalized itinerary:', error);
        
        // Show error in the completion message
        if (completionMessage) {
            completionMessage.innerHTML = `
                <div style="text-align: center; padding: 30px; background: linear-gradient(135deg, #f56565, #e53e3e); color: white; border-radius: 15px;">
                    <h3 style="margin-bottom: 15px;"><i class="fas fa-exclamation-triangle"></i> Error</h3>
                    <p style="margin-bottom: 20px;">${error.message}</p>
                    <button onclick="generatePersonalizedItinerary()" style="background: white; color: #e53e3e; border: none; padding: 12px 25px; border-radius: 8px; font-weight: 600; cursor: pointer;">
                        <i class="fas fa-retry"></i> Try Again
                    </button>
                </div>
            `;
        }
    }
}

// Display sectioned itinerary (Legacy)
function displaySectionedItinerary(sections) {
    itinerarySections.innerHTML = '';
    
    sections.forEach((section, index) => {
        const sectionElement = createSectionElement(section, index);
        itinerarySections.appendChild(sectionElement);
    });
}

// Create individual section element
function createSectionElement(section, index) {
    const sectionDiv = document.createElement('div');
    sectionDiv.className = 'itinerary-section';
    sectionDiv.dataset.sectionId = section.id || index;
    
    const iconMap = {
        'day': 'fas fa-calendar-day',
        'restaurant': 'fas fa-utensils',
        'accommodation': 'fas fa-bed',
        'activity': 'fas fa-star',
        'transportation': 'fas fa-car',
        'general': 'fas fa-info-circle'
    };
    
    const iconClass = iconMap[section.type] || iconMap['general'];
    
    sectionDiv.innerHTML = `
        <div class="section-header">
            <div class="section-title">
                <div class="section-type-icon ${section.type}">
                    <i class="${iconClass}"></i>
                </div>
                ${section.title || `Section ${index + 1}`}
            </div>
            <div class="section-actions">
                <button class="edit-section-btn" onclick="toggleSectionChat(${section.id || index})">
                    <i class="fas fa-edit"></i>
                    Edit
                </button>
            </div>
        </div>
        <div class="section-content">
            ${formatItinerary(section.content)}
        </div>
        <div class="section-chat" id="chat-${section.id || index}">
            <div class="chat-input-container">
                <textarea 
                    class="section-chat-input" 
                    placeholder="What would you like to change about this section? (e.g., 'Change the restaurant to something more budget-friendly' or 'Move this activity to earlier in the day')"
                    rows="2"
                ></textarea>
                <button class="send-edit-btn" onclick="sendSectionEdit(${section.id || index})">
                    <i class="fas fa-paper-plane"></i>
                    Send
                </button>
            </div>
            <div class="chat-status" id="status-${section.id || index}"></div>
        </div>
    `;
    
    return sectionDiv;
}

// Toggle section chat visibility
function toggleSectionChat(sectionId) {
    const chatElement = document.getElementById(`chat-${sectionId}`);
    const isActive = chatElement.classList.contains('active');
    
    // Close all other chats
    document.querySelectorAll('.section-chat.active').forEach(chat => {
        chat.classList.remove('active');
    });
    activeChatSections.clear();
    
    // Toggle current chat
    if (!isActive) {
        chatElement.classList.add('active');
        activeChatSections.add(sectionId);
        
        // Focus on the input
        const input = chatElement.querySelector('.section-chat-input');
        setTimeout(() => input.focus(), 100);
    }
}

// Send section edit request
async function sendSectionEdit(sectionId) {
    const chatElement = document.getElementById(`chat-${sectionId}`);
    const input = chatElement.querySelector('.section-chat-input');
    const sendBtn = chatElement.querySelector('.send-edit-btn');
    const status = document.getElementById(`status-${sectionId}`);
    
    const editRequest = input.value.trim();
    if (!editRequest) {
        showChatStatus(status, 'Please enter your edit request.', 'error');
        return;
    }
    
    // Find the section content
    const section = currentSections.find(s => (s.id || currentSections.indexOf(s)) == sectionId);
    if (!section) {
        showChatStatus(status, 'Section not found.', 'error');
        return;
    }
    
    // Disable input and button
    input.disabled = true;
    sendBtn.disabled = true;
    showChatStatus(status, 'Processing your edit...', 'loading');
    
    try {
        const response = await fetch('/edit_section', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                full_itinerary: currentItinerary,
                section_id: sectionId,
                section_content: section.content,
                edit_request: editRequest
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to edit section');
        }
        
        if (data.success) {
            // Update the current itinerary and sections
            currentItinerary = data.updated_itinerary;
            currentSections = data.updated_sections;
            
            // Refresh the display
            displaySectionedItinerary(currentSections);
            
            showChatStatus(status, 'Section updated successfully!', 'success');
            
            // Clear input
            input.value = '';
            
            // Close chat after a delay
            setTimeout(() => {
                chatElement.classList.remove('active');
                activeChatSections.delete(sectionId);
            }, 2000);
            
        } else {
            throw new Error(data.error || 'Unknown error occurred');
        }
        
    } catch (error) {
        console.error('Error editing section:', error);
        showChatStatus(status, error.message || 'Failed to edit section. Please try again.', 'error');
    } finally {
        // Re-enable input and button
        input.disabled = false;
        sendBtn.disabled = false;
    }
}

// Show chat status message
function showChatStatus(statusElement, message, type) {
    statusElement.textContent = message;
    statusElement.className = `chat-status ${type}`;
    
    if (type === 'loading') {
        statusElement.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${message}`;
    } else if (type === 'success') {
        statusElement.innerHTML = `<i class="fas fa-check"></i> ${message}`;
    } else if (type === 'error') {
        statusElement.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
    }
}

// Add some error handling for network issues
window.addEventListener('online', () => {
    if (errorSection.classList.contains('hidden') === false) {
        // If we're showing an error and we're back online, show a retry option
        const retryMessage = document.createElement('p');
        retryMessage.textContent = 'Connection restored! You can try again now.';
        retryMessage.style.color = '#48bb78';
        retryMessage.style.fontWeight = '500';
        errorSection.querySelector('.error-container').appendChild(retryMessage);
    }
});

window.addEventListener('offline', () => {
    if (loadingSection.classList.contains('hidden') === false) {
        showError('No internet connection. Please check your connection and try again.');
    }
});
