// Enhanced renderer.js for Friday AI UI
// DOM Elements
const conversationHistory = document.getElementById('conversation-history');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-btn');
const microphoneButton = document.getElementById('microphone-btn');
const onlineIndicator = document.getElementById('online-indicator').querySelector('.indicator-dot');
const processingIndicator = document.getElementById('processing-indicator').querySelector('.indicator-dot');
const recordingIndicator = document.getElementById('recording-indicator');
const onlineToggle = document.getElementById('online-toggle');
const onlineStatusText = onlineToggle.querySelector('.online-status-text');
const onlineSwitch = document.getElementById('online-switch');
const cpuUsage = document.getElementById('cpu-usage');
const memoryUsage = document.getElementById('memory-usage');
const diskUsage = document.getElementById('disk-usage');
const currentTime = document.getElementById('current-time');
const weatherDisplay = document.getElementById('weather-display');

// Create Command Deck button
const commandDeckButton = document.createElement('button');
commandDeckButton.id = 'command-deck-btn';
commandDeckButton.className = 'action-button';
commandDeckButton.title = 'Open Command Deck';
commandDeckButton.innerHTML = '<i class="fas fa-tachometer-alt"></i>';

// Configuration
const FRIDAY_API_URL = 'http://localhost:5000'; // Make sure this matches your HTTP controller port

// System info variables
let systemInfoUpdateInterval = null;
let lastSystemInfo = null;

// Speech recognition state
let isRecording = false;
let isProcessing = false;

// Initialize marked for markdown rendering
const marked = window.marked;
if (marked) {
    marked.setOptions({
        renderer: new marked.Renderer(),
        highlight: function(code, language) {
            return hljs.highlightAuto(code).value;
        },
        gfm: true,
        breaks: true
    });
}

// Add this function to open the Command Deck
async function openCommandDeck() {
    try {
        // First try using Electron API if available
        if (window.electronAPI && window.electronAPI.openCommandDeck) {
            const result = await window.electronAPI.openCommandDeck();
            if (!result.success) {
                showNotification(result.error || 'Could not open Command Deck', 'error');
            }
            return;
        }
        
        // Fallback to direct API call
        const response = await fetch(`${FRIDAY_API_URL}/status`);
        if (response.ok) {
            const status = await response.json();
            
            if (status.command_deck_available) {
                // Open Command Deck in a new window
                window.open(`${FRIDAY_API_URL}/dashboard`, '_blank');
            } else {
                showNotification('Command Deck is not available. Please start Friday with Command Deck enabled.', 'warning');
            }
        } else {
            showNotification('Could not connect to Friday API', 'error');
        }
    } catch (error) {
        console.error('Error opening Command Deck:', error);
        showNotification('Error opening Command Deck', 'error');
    }
}

// Initialize Command Deck button
function initializeCommandDeckButton() {
    // Add the Command Deck button to the conversation actions
    const conversationActions = document.querySelector('.conversation-actions');
    if (conversationActions) {
        conversationActions.insertBefore(commandDeckButton, conversationActions.firstChild);
        
        // Add event listener
        commandDeckButton.addEventListener('click', openCommandDeck);
    }
}

// Initialize Friday UI
function initializeFridayUI() {
    console.log('Initializing Friday UI...');
    
    // Add welcome message
    addMessage({
        text: "Hello! I'm Friday, your personal AI assistant. How can I help you today?",
        sender: 'friday',
        timestamp: new Date().toISOString()
    });
    
    // Set up event listeners 
    // Fix for send button - using direct click handler
    if (sendButton) {
        console.log('Setting up send button event listener');
        sendButton.onclick = function() {
            console.log('Send button clicked!');
            sendUserMessage();
        };
    } else {
        console.error('Send button not found in DOM');
    }
    
    // Set up enter key handler
    if (userInput) {
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                console.log('Enter key pressed!');
                e.preventDefault();
                sendUserMessage();
            }
        });
        
        // Set up auto-resize for textarea
        userInput.addEventListener('input', adjustTextareaHeight);
        
        // Initial textarea height adjustment
        adjustTextareaHeight();
    } else {
        console.error('User input textarea not found in DOM');
    }
    
    // Microphone button
    if (microphoneButton) {
        microphoneButton.addEventListener('click', toggleSpeechInput);
    }
    
    // Set up online toggle
    if (onlineSwitch) {
        onlineSwitch.addEventListener('change', async () => {
            const result = await window.electronAPI.toggleOnlineStatus();
            if (result.success) {
                updateOnlineToggle(result.online);
            } else {
                console.error('Failed to toggle online status:', result.error);
                // Revert the switch to match current status
                onlineSwitch.checked = !onlineSwitch.checked;
            }
        });
    }
    
    // Initialize Command Deck button
    initializeCommandDeckButton();
    
    // Initialize recording indicator state
    if (recordingIndicator) {
        recordingIndicator.style.display = 'none';
    }
    
    // Start system information updates from API endpoint
    updateSystemInfoFromAPI();
    systemInfoUpdateInterval = setInterval(updateSystemInfoFromAPI, 5000); // Update every 5 seconds
    
    // Fallback to electron API for system info
    updateSystemInfo();
    
    // Start time updates
    updateTime();
    setInterval(updateTime, 1000); // Update every second
    
    // Check Friday status
    checkFridayStatus();
    
    // Focus on the textarea
    if (userInput) {
        userInput.focus();
    }
    
    console.log('Friday UI initialized successfully');
}

// Improved textarea height adjustment
function adjustTextareaHeight() {
    if (!userInput) return;
    
    // Reset height to auto first to correctly calculate new height
    userInput.style.height = 'auto';
    
    // Calculate the scrollHeight and set the new height
    const newHeight = Math.max(40, userInput.scrollHeight);
    userInput.style.height = `${newHeight}px`;
    
    // Update parent container if needed
    const inputContainer = document.getElementById('input-container');
    if (inputContainer) {
        inputContainer.style.paddingBottom = newHeight > 80 ? '15px' : '25px';
    }
    
    console.log(`Adjusted textarea height to ${newHeight}px`);
}

// System info update from API
function updateSystemInfoFromAPI() {
    fetch(`${FRIDAY_API_URL}/api/system_info`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                lastSystemInfo = data;
                
                // Update UI elements
                if (cpuUsage) cpuUsage.textContent = `CPU: ${data.metrics.cpu.usage_percent}%`;
                if (memoryUsage) memoryUsage.textContent = `Memory: ${data.metrics.memory.usage_percent}%`;
                if (diskUsage) diskUsage.textContent = `Disk: ${data.metrics.disk.usage_percent}%`;
                
                // Update weather if available
                if (data.weather && !data.weather.error) {
                    updateWeatherInfo(data.weather);
                }
            }
        })
        .catch(error => {
            console.error('Error fetching system info from API:', error);
            // Fall back to electron API
            updateSystemInfo();
        });
}

// Fallback system info from electron API
function updateSystemInfo() {
    // Get system information from the main process
    if (window.electronAPI && window.electronAPI.getSystemInfo) {
        window.electronAPI.getSystemInfo()
            .then(info => {
                if (cpuUsage) cpuUsage.textContent = `CPU: ${info.cpu}%`;
                if (memoryUsage) memoryUsage.textContent = `Memory: ${info.memory}%`;
                if (diskUsage) diskUsage.textContent = `Disk: ${info.disk}%`;
            })
            .catch(error => {
                console.error('Error getting system info from electron:', error);
            });
    }
}

// Weather info update
function updateWeatherInfo(weather) {
    // Skip if weather element doesn't exist or weather data isn't available
    if (!weatherDisplay || !weather || weather.error) return;
    
    // Format weather information
    const temperature = weather.temperature?.current || 'N/A';
    const condition = weather.condition?.description || 'N/A';
    const location = weather.location || 'Unknown';
    
    // Update the weather display
    weatherDisplay.innerHTML = `
        <div class="weather-icon">
            <i class="fas fa-${getWeatherIcon(condition)}"></i>
        </div>
        <div class="weather-details">
            <div class="weather-temp">${temperature}°C</div>
            <div class="weather-cond">${condition}</div>
            <div class="weather-loc">${location}</div>
        </div>
    `;
    
    // Show the weather display
    weatherDisplay.style.display = 'flex';
}

// Helper function to get appropriate weather icon
function getWeatherIcon(condition) {
    if (!condition) return 'cloud';
    
    condition = condition.toLowerCase();
    
    if (condition.includes('clear') || condition.includes('sunny')) {
        return 'sun';
    } else if (condition.includes('cloud')) {
        return 'cloud';
    } else if (condition.includes('rain') || condition.includes('drizzle')) {
        return 'cloud-rain';
    } else if (condition.includes('snow')) {
        return 'snowflake';
    } else if (condition.includes('thunder') || condition.includes('storm')) {
        return 'bolt';
    } else if (condition.includes('fog') || condition.includes('mist')) {
        return 'smog';
    } else {
        return 'cloud';
    }
}

// Get initial online status
if (window.electronAPI && window.electronAPI.getOnlineStatus) {
    window.electronAPI.getOnlineStatus().then((online) => {
        updateOnlineToggle(online);
        if (onlineSwitch) onlineSwitch.checked = online;
    }).catch(error => {
        console.error('Error getting initial online status:', error);
    });
}

function updateOnlineToggle(online) {
    if (!onlineToggle || !onlineStatusText) return;
    
    if (online) {
        onlineToggle.classList.remove('offline');
        onlineToggle.classList.add('online');
        onlineStatusText.textContent = 'Online';
    } else {
        onlineToggle.classList.remove('online');
        onlineToggle.classList.add('offline');
        onlineStatusText.textContent = 'Offline';
    }
}

function checkFridayStatus() {
    fetch(`${FRIDAY_API_URL}/status`)
        .then(response => response.json())
        .then(status => {
            console.log('Friday status:', status);
            updateStatus(status);
        })
        .catch(error => {
            console.error('Error checking Friday status:', error);
            if (onlineIndicator) onlineIndicator.classList.remove('online');
            if (processingIndicator) processingIndicator.classList.remove('processing');
            
            // Try again after a delay
            setTimeout(checkFridayStatus, 5000);
        });
}

function sendUserMessage() {
    console.log('sendUserMessage called');
    const text = userInput ? userInput.value.trim() : '';
    if (!text || isProcessing) {
        console.log('Not sending: empty text or already processing');
        return;
    }
    
    console.log('Sending user message:', text);
    
    // First check if this is a search request
    if (text.toLowerCase().startsWith("search for") || text.toLowerCase().startsWith("search the web for")) {
        // Extract search query
        const searchQuery = text.replace(/^search(\s+the\s+web)?\s+for\s+/i, "").trim();
        if (searchQuery) {
            // Add message to conversation
            addMessage({
                text,
                sender: 'user',
                timestamp: new Date().toISOString()
            });
            
            // Clear input and reset height
            userInput.value = '';
            adjustTextareaHeight();
            
            // Perform web search
            performWebSearch(searchQuery);
            return;
        }
    }
    
    // Add message to conversation
    addMessage({
        text,
        sender: 'user',
        timestamp: new Date().toISOString()
    });
    
    // Clear input and reset height
    userInput.value = '';
    adjustTextareaHeight();
    
    // Show processing indicator
    isProcessing = true;
    if (processingIndicator) processingIndicator.classList.add('processing');
    
    // Add a typing indicator message from Friday
    const typingMessageId = addTypingIndicator();
    
    // Check if we should use enhanced prompt with context
    const shouldUseEnhancedPrompt = true; // Could be configurable in the future

    if (shouldUseEnhancedPrompt) {
        // First try enriching the prompt with context
        fetch(`${FRIDAY_API_URL}/api/enrich_prompt`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                prompt: text,
                include_web_search: false // Set to true to include web search results
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to enrich prompt');
            }
            return response.json();
        })
        .then(enrichData => {
            if (enrichData.success) {
                // Now send enriched prompt to message endpoint
                return fetch(`${FRIDAY_API_URL}/message`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: enrichData.enriched_prompt })
                });
            } else {
                // Fall back to regular message endpoint
                return fetch(`${FRIDAY_API_URL}/message`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text })
                });
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to get response from Friday');
            }
            return response.json();
        })
        .then(data => handleFridayResponse(data, typingMessageId))
        .catch(error => {
            console.error('Error with enhanced prompt flow:', error);
            
            // Fall back to standard message flow
            standardMessageFlow(text, typingMessageId);
        });
    } else {
        // Use standard message flow
        standardMessageFlow(text, typingMessageId);
    }
}

// Standard message flow without enhancements
function standardMessageFlow(text, typingMessageId) {
    fetch(`${FRIDAY_API_URL}/message`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    })
    .then(response => response.json())
    .then(data => handleFridayResponse(data, typingMessageId))
    .catch(error => {
        handleSendError(error, typingMessageId);
    });
}

// Handle Friday's response
function handleFridayResponse(data, typingMessageId) {
    console.log('Friday response:', data);
    isProcessing = false;
    if (processingIndicator) processingIndicator.classList.remove('processing');
    
    // Remove typing indicator
    removeTypingIndicator(typingMessageId);
    
    // Add response to conversation
    addMessage({
        text: data.text,
        sender: 'friday',
        timestamp: data.timestamp || new Date().toISOString()
    });
    
    // Speak the response
    speakText(data.text);
    
    // Focus on input field again
    if (userInput) userInput.focus();
}

// Handle send error
function handleSendError(error, typingMessageId) {
    console.error('Error sending message to Friday:', error);
    isProcessing = false;
    if (processingIndicator) processingIndicator.classList.remove('processing');
    
    // Remove typing indicator
    removeTypingIndicator(typingMessageId);
    
    // Add error message
    addMessage({
        text: "I'm sorry, I couldn't connect to the Friday backend. Please check your connection and try again.",
        sender: 'friday',
        timestamp: new Date().toISOString()
    });
    
    // Check status
    checkFridayStatus();
    
    // Focus on input field again
    if (userInput) userInput.focus();
}

// Web search function
function performWebSearch(query) {
    if (!query) return;
    
    // Show processing indicator
    isProcessing = true;
    if (processingIndicator) processingIndicator.classList.add('processing');
    
    // Add searching message
    addMessage({
        text: `Searching the web for: "${query}"...`,
        sender: 'friday',
        timestamp: new Date().toISOString()
    });
    
    // Add typing indicator
    const typingMessageId = addTypingIndicator();
    
    // Call the web search API
    fetch(`${FRIDAY_API_URL}/api/web_search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            query: query,
            num_results: 5,
            browse_results: true
        })
    })
    .then(response => response.json())
    .then(data => {
        // Remove typing indicator
        removeTypingIndicator(typingMessageId);
        isProcessing = false;
        if (processingIndicator) processingIndicator.classList.remove('processing');
        
        if (data.success) {
            // Format search results
            let resultsText = `Here's what I found for "${query}":\n\n`;
            
            data.results.forEach((result, index) => {
                resultsText += `${index + 1}. **${result.title}**\n`;
                resultsText += `   URL: ${result.url}\n`;
                resultsText += `   ${result.snippet}\n\n`;
                
                // Add page content if available
                if (result.page_content) {
                    resultsText += `   Content: ${result.page_content.substring(0, 200)}...\n\n`;
                }
            });
            
            // Add message with results
            addMessage({
                text: resultsText,
                sender: 'friday',
                timestamp: new Date().toISOString()
            });
        } else {
            // Show error message
            addMessage({
                text: `I couldn't find information for "${query}": ${data.error || 'Unknown error'}`,
                sender: 'friday',
                timestamp: new Date().toISOString()
            });
        }
        
        // Focus on input field again
        if (userInput) userInput.focus();
    })
    .catch(error => {
        // Remove typing indicator
        removeTypingIndicator(typingMessageId);
        isProcessing = false;
        if (processingIndicator) processingIndicator.classList.remove('processing');
        
        console.error('Error performing web search:', error);
        addMessage({
            text: `I encountered an error while searching for "${query}".`,
            sender: 'friday',
            timestamp: new Date().toISOString()
        });
        
        // Focus on input field again
        if (userInput) userInput.focus();
    });
}

function addTypingIndicator() {
    const typingElement = document.createElement('div');
    const messageId = 'typing-' + Date.now();
    typingElement.id = messageId;
    typingElement.classList.add('message', 'friday');
    
    typingElement.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="message-content">
            <div class="message-text">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        </div>
    `;
    
    if (conversationHistory) {
        conversationHistory.appendChild(typingElement);
        
        // Scroll to bottom
        conversationHistory.scrollTop = conversationHistory.scrollHeight;
    }
    
    return messageId;
}

function removeTypingIndicator(messageId) {
    const typingElement = document.getElementById(messageId);
    if (typingElement) {
        typingElement.remove();
    }
}

function toggleSpeechInput() {
    if (isRecording) {
        stopSpeechRecognition();
    } else {
        startSpeechRecognition();
    }
}

function startSpeechRecognition() {
    fetch(`${FRIDAY_API_URL}/speech/start`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Speech recognition started:', data);
        if (data.success) {
            isRecording = true;
            if (microphoneButton) microphoneButton.classList.add('recording');
            if (recordingIndicator) recordingIndicator.style.display = 'flex';
        } else {
            showNotification(`Failed to start speech recognition: ${data.error || 'Unknown error'}`, 'error');
        }
    })
    .catch(error => {
        console.error('Error starting speech recognition:', error);
        showNotification('Failed to start speech recognition. Please try again.', 'error');
    });
}

function stopSpeechRecognition() {
    // Show processing indicator
    isProcessing = true;
    if (processingIndicator) processingIndicator.classList.add('processing');
    if (recordingIndicator) {
        recordingIndicator.innerHTML = '<div class="recording-icon"></div><span>Processing speech...</span>';
    }
    
    fetch(`${FRIDAY_API_URL}/speech/stop`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Speech recognition stopped:', data);
        isRecording = false;
        isProcessing = false;
        if (microphoneButton) microphoneButton.classList.remove('recording');
        if (recordingIndicator) recordingIndicator.style.display = 'none';
        if (processingIndicator) processingIndicator.classList.remove('processing');
        
        if (data.transcription) {
            // Add transcription to conversation
            addMessage({
                text: data.transcription,
                sender: 'user',
                timestamp: data.timestamp || new Date().toISOString()
            });
            
            // Add response if available
            if (data.response) {
                addMessage({
                    text: data.response,
                    sender: 'friday',
                    timestamp: data.timestamp || new Date().toISOString()
                });
            }
        } else if (data.error) {
            showNotification(`Speech recognition error: ${data.error}`, 'error');
        }
        
        // Focus on input field again
        if (userInput) userInput.focus();
    })
    .catch(error => {
        console.error('Error stopping speech recognition:', error);
        isRecording = false;
        isProcessing = false;
        if (microphoneButton) microphoneButton.classList.remove('recording');
        if (recordingIndicator) recordingIndicator.style.display = 'none';
        if (processingIndicator) processingIndicator.classList.remove('processing');
        showNotification('Failed to process speech. Please try again.', 'error');
        
        // Focus on input field again
        if (userInput) userInput.focus();
    });
}

function speakText(text) {
    fetch(`${FRIDAY_API_URL}/speech/speak`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Text-to-speech result:', data);
    })
    .catch(error => {
        console.error('Error with text-to-speech:', error);
    });
}

function updateStatus(status) {
    if (status.online !== undefined) {
        if (status.online) {
            if (onlineIndicator) onlineIndicator.classList.add('online');
        } else {
            if (onlineIndicator) onlineIndicator.classList.remove('online');
        }
        
        // Update toggle too
        updateOnlineToggle(status.online);
        if (onlineSwitch) onlineSwitch.checked = status.online;
    }
    
    if (status.processing !== undefined) {
        if (status.processing) {
            if (processingIndicator) processingIndicator.classList.add('processing');
        } else {
            if (processingIndicator) processingIndicator.classList.remove('processing');
        }
    }
}

function addMessage(message) {
    if (!conversationHistory) return;
    
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', message.sender);
    
    // Create avatar based on sender
    const avatarIcon = message.sender === 'friday' ? 'robot' : 'user';
    
    // Format message text with markdown if it's from Friday
    let messageText = message.text;
    if (message.sender === 'friday' && window.marked) {
        // Check if message contains code blocks
        if (messageText.includes('```')) {
            messageText = formatCodeBlocks(messageText);
        } else {
            messageText = marked.parse(messageText);
        }
    }
    
    messageElement.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-${avatarIcon}"></i>
        </div>
        <div class="message-content">
            <div class="message-text${message.sender === 'friday' ? ' markdown-content' : ''}">
                ${messageText}
            </div>
            <div class="message-timestamp">${formatTimestamp(message.timestamp)}</div>
        </div>
    `;
    
    conversationHistory.appendChild(messageElement);
    
    // Scroll to bottom
    conversationHistory.scrollTop = conversationHistory.scrollHeight;
}

function formatCodeBlocks(text) {
    // Pattern to find code blocks with language specification
    const codeBlockPattern = /```(\w+)?\n([\s\S]*?)```/g;
    
    // Replace code blocks with properly formatted HTML
    let formattedText = text.replace(codeBlockPattern, (match, language, code) => {
        const lang = language || '';
        return `<div class="code-block${lang ? ' ' + lang : ''}"><pre><code class="${lang}">${escapeHtml(code.trim())}</code></pre></div>`;
    });
    
    // Process remaining text with marked
    if (window.marked) {
        formattedText = marked.parse(formattedText);
    }
    
    return formattedText;
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function updateTime() {
    const now = new Date();
    if (currentTime) {
        currentTime.textContent = now.toLocaleTimeString();
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.classList.add('notification', type);
    notification.textContent = message;
    
    // Add icon based on type
    const icon = document.createElement('i');
    icon.classList.add('fas');
    
    if (type === 'error') {
        icon.classList.add('fa-exclamation-circle');
    } else if (type === 'success') {
        icon.classList.add('fa-check-circle');
    } else {
        icon.classList.add('fa-info-circle');
    }
    
    notification.prepend(icon);
    
    // Add close button
    const closeBtn = document.createElement('button');
    closeBtn.classList.add('notification-close');
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', () => {
        notification.remove();
    });
    
    notification.appendChild(closeBtn);
    
    // Add to document
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 5000);
}

// Stop system info updates when window is closing
window.addEventListener('beforeunload', () => {
    if (systemInfoUpdateInterval) {
        clearInterval(systemInfoUpdateInterval);
    }
});

// Initialize the UI when the page loads
document.addEventListener('DOMContentLoaded', initializeFridayUI);

// Periodically check Friday status
setInterval(checkFridayStatus, 30000);  // Every 30 seconds

// Add preconnect for API URL
const linkElement = document.createElement('link');
linkElement.rel = 'preconnect';
linkElement.href = FRIDAY_API_URL;
document.head.appendChild(linkElement);

// Add CSS for the Command Deck button
const commandDeckStyle = document.createElement('style');
commandDeckStyle.textContent = `
#command-deck-btn {
    color: var(--accent-color);
    font-size: 18px;
}

#command-deck-btn:hover {
    color: var(--primary-color);
}
`;
document.head.appendChild(commandDeckStyle);