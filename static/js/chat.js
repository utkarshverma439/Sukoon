// Chat functionality
let currentBot = 'aarav';
let isInCall = false;
let recognition = null;
let synthesis = window.speechSynthesis;

const botInfo = {
    aarav: {
        name: 'Aarav',
        description: 'Calm & Logical Support',
        avatar: '/static/images/aarav.png',
        accent: '#00d4aa'
    },
    meera: {
        name: 'Meera', 
        description: 'Warm & Empathetic Support',
        avatar: '/static/images/meera.png',
        accent: '#667eea'
    }
};

document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
    loadChatHistory();
});

function initializeChat() {
    // Initialize speech recognition if available
    try {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true; // Enable interim results for better responsiveness
            recognition.lang = 'en-US'; // Changed to en-US for better compatibility
            recognition.maxAlternatives = 1;
            recognition.started = false;
            
            // Add event handlers directly during initialization
            recognition.onstart = function() {
                console.log('Voice recognition started');
                recognition.started = true;
            };
            
            console.log('Voice recognition initialized successfully');
        } else {
            console.log('Voice recognition not supported in this browser');
            // Show a notification to the user
            alert('Voice recognition is not supported in your browser. Please try using Chrome, Edge, or Safari.');
        }
    } catch (error) {
        console.error('Error initializing speech recognition:', error);
    }
}

function setupEventListeners() {
    // Bot tab switching
    document.querySelectorAll('.bot-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            if (!this.classList.contains('active')) {
                switchBot(this.dataset.bot);
            }
        });
    });
    
    // Send message
    document.getElementById('send-btn').addEventListener('click', sendMessage);
    
    const messageInput = document.getElementById('message-input');
    
    // Handle Enter key and auto-resize
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Auto-resize textarea
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        
        // Enhanced send button animation
        const sendBtn = document.getElementById('send-btn');
        if (this.value.trim()) {
            sendBtn.style.background = 'linear-gradient(135deg, #00d4aa, #0084ff)';
            sendBtn.style.transform = 'scale(1.1)';
            sendBtn.style.boxShadow = '0 4px 15px rgba(0, 212, 170, 0.4)';
        } else {
            sendBtn.style.background = '';
            sendBtn.style.transform = '';
            sendBtn.style.boxShadow = '';
        }
    });
    
    // Voice recognition button
    document.getElementById('voice-btn').addEventListener('click', openVoiceModal);
    
    // Voice modal controls
    document.getElementById('start-voice-btn').addEventListener('click', startVoiceRecognition);
    document.getElementById('stop-voice-recording').addEventListener('click', stopVoiceRecognition);
    document.getElementById('send-voice-text').addEventListener('click', sendVoiceText);
    document.getElementById('close-voice-modal').addEventListener('click', closeVoiceModal);
    document.getElementById('send-fallback-btn').addEventListener('click', sendFallbackText);
    
    // Chat actions
    document.getElementById('clear-chat-btn').addEventListener('click', clearCurrentChat);
    document.getElementById('clear-all-btn').addEventListener('click', clearAllData);
    
    // Emoji functionality
    document.getElementById('emoji-btn').addEventListener('click', toggleEmojiPicker);
    
    // Emoji picker items
    document.querySelectorAll('.emoji-item').forEach(emoji => {
        emoji.addEventListener('click', function() {
            insertEmoji(this.dataset.emoji);
        });
    });
    
    // Close emoji picker when clicking outside
    document.addEventListener('click', function(e) {
        const emojiPicker = document.getElementById('emoji-picker');
        const emojiBtn = document.getElementById('emoji-btn');
        
        if (!emojiPicker.contains(e.target) && !emojiBtn.contains(e.target)) {
            emojiPicker.style.display = 'none';
        }
    });
    
    // Close modal when clicking outside
    document.getElementById('voice-modal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeVoiceModal();
        }
    });
}

function switchBot(botName) {
    currentBot = botName;
    
    // Update active tab
    document.querySelectorAll('.bot-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`[data-bot="${botName}"]`).classList.add('active');
    
    // Update current bot info
    const bot = botInfo[botName];
    document.getElementById('current-bot-avatar').src = bot.avatar;
    document.getElementById('current-bot-name').textContent = bot.name;
    document.getElementById('current-bot-desc').textContent = bot.description;
    
    // Load chat history for this bot
    loadChatHistory();
}

async function loadChatHistory() {
    try {
        const response = await fetch(`/api/chats/${currentBot}`);
        if (response.ok) {
            const chats = await response.json();
            displayChatHistory(chats);
        }
    } catch (error) {
        console.error('Error loading chat history:', error);
    }
}

function displayChatHistory(chats) {
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = '';
    
    if (chats.length === 0) {
        messagesContainer.innerHTML = `
            <div class="welcome-message">
                <p>Hi! I'm ${botInfo[currentBot].name}. I'm here to listen and support you. How are you feeling today?</p>
            </div>
        `;
        return;
    }
    
    chats.forEach(chat => {
        addMessageToChat(chat.message, 'user');
        addMessageToChat(chat.reply, 'bot');
    });
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addMessageToChat(message, sender) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    messageDiv.textContent = message;
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addMessageToChat(message, 'user');
    input.value = '';
    input.style.height = 'auto'; // Reset height
    
    // Reset send button
    const sendBtn = document.getElementById('send-btn');
    sendBtn.style.background = '';
    sendBtn.style.transform = '';
    sendBtn.style.boxShadow = '';
    
    // Show typing indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot typing';
    typingDiv.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
    document.getElementById('chat-messages').appendChild(typingDiv);
    
    try {
        const response = await fetch(`/chat/${currentBot}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                message: message,
                via_call: isInCall 
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Remove typing indicator
            typingDiv.remove();
            
            // Add bot response
            addMessageToChat(data.reply, 'bot');
            
            // If in call, speak the response
            if (isInCall) {
                speakText(data.reply);
            }
        } else {
            typingDiv.textContent = 'Sorry, I encountered an error. Please try again.';
        }
    } catch (error) {
        console.error('Error sending message:', error);
        typingDiv.textContent = 'Sorry, I encountered an error. Please try again.';
    }
}

// Voice Recognition Functions
function openVoiceModal() {
    const modal = document.getElementById('voice-modal');
    const statusText = document.getElementById('voice-status-text');
    const transcript = document.getElementById('voice-transcript');
    
    // Reset modal state
    statusText.textContent = 'Click the microphone to start speaking...';
    transcript.textContent = '';
    document.getElementById('start-voice-btn').style.display = 'inline-block';
    document.getElementById('stop-voice-recording').style.display = 'none';
    document.getElementById('send-voice-text').style.display = 'none';
    
    modal.style.display = 'block';
}

function closeVoiceModal() {
    const modal = document.getElementById('voice-modal');
    modal.style.display = 'none';
    
    // Stop recognition if running
    if (recognition && recognition.started) {
        recognition.stop();
    }
    
    // Reset voice button state
    const voiceBtn = document.getElementById('voice-btn');
    voiceBtn.classList.remove('recording', 'listening', 'processing');
}

function startVoiceRecognition() {
    if (!recognition) {
        alert('Voice recognition is not supported in your browser. Please use the text input instead or try Chrome/Edge.');
        return;
    }
    
    const statusText = document.getElementById('voice-status-text');
    const voiceBtn = document.getElementById('voice-btn');
    const transcript = document.getElementById('voice-transcript');
    
    // Clear previous transcript
    transcript.textContent = '';
    
    try {
        statusText.textContent = 'Listening... Please speak now.';
        voiceBtn.classList.add('listening');
        
        document.getElementById('start-voice-btn').style.display = 'none';
        document.getElementById('stop-voice-recording').style.display = 'inline-block';
        
        // Set up event handlers before starting recognition
        recognition.onresult = function(event) {
            // Get the latest result
            const results = event.results;
            const latestResult = results[results.length - 1];
            const latestTranscript = latestResult[0].transcript;
            
            // Update the transcript
            transcript.textContent = latestTranscript;
            
            // If this is a final result, show the send button
            if (latestResult.isFinal) {
                statusText.textContent = 'Speech recognized! You can send it or speak again.';
                document.getElementById('send-voice-text').style.display = 'inline-block';
                voiceBtn.classList.remove('listening');
                voiceBtn.classList.add('processing');
            }
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
            statusText.textContent = 'Error: ' + event.error + '. Please try again or use text input.';
            resetVoiceRecognition();
        };
        
        recognition.onend = function() {
            recognition.started = false;
            if (!transcript.textContent) {
                statusText.textContent = 'No speech detected. Please try again.';
                resetVoiceRecognition();
            }
        };
        
        // Start recognition
        recognition.start();
        recognition.started = true;
        
    } catch (error) {
        console.error('Voice recognition error:', error);
        statusText.textContent = 'Error starting voice recognition: ' + error.message;
        resetVoiceRecognition();
    }
}

function stopVoiceRecognition() {
    if (recognition && recognition.started) {
        recognition.stop();
    }
    resetVoiceRecognition();
}

function resetVoiceRecognition() {
    const voiceBtn = document.getElementById('voice-btn');
    voiceBtn.classList.remove('recording', 'listening', 'processing');
    
    document.getElementById('start-voice-btn').style.display = 'inline-block';
    document.getElementById('stop-voice-recording').style.display = 'none';
    
    if (recognition) {
        recognition.started = false;
    }
}

async function sendVoiceText() {
    const transcript = document.getElementById('voice-transcript').textContent.trim();
    
    if (!transcript) {
        alert('No text to send. Please speak first.');
        return;
    }
    
    // Close modal and send message
    closeVoiceModal();
    
    // Set the message in the input and send
    document.getElementById('message-input').value = transcript;
    await sendMessage();
}

async function sendFallbackText() {
    const fallbackInput = document.getElementById('voice-fallback-input');
    const message = fallbackInput.value.trim();
    
    if (!message) {
        alert('Please enter a message.');
        return;
    }
    
    // Close modal and send message
    closeVoiceModal();
    
    // Set the message in the input and send
    document.getElementById('message-input').value = message;
    await sendMessage();
    
    fallbackInput.value = '';
}

function speakText(text) {
    if (!synthesis) return;
    
    // Cancel any ongoing speech
    synthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Set voice parameters based on bot
    if (currentBot === 'aarav') {
        utterance.pitch = 0.8;
        utterance.rate = 0.95;
    } else {
        utterance.pitch = 1.05;
        utterance.rate = 1.0;
    }
    
    utterance.lang = 'en-IN';
    
    // Try to find an appropriate voice
    const voices = synthesis.getVoices();
    const preferredVoice = voices.find(voice => 
        voice.lang.includes('en-IN') || voice.lang.includes('hi-IN')
    );
    
    if (preferredVoice) {
        utterance.voice = preferredVoice;
    }
    
    synthesis.speak(utterance);
}

// Emoji Functions
function toggleEmojiPicker() {
    const emojiPicker = document.getElementById('emoji-picker');
    const isVisible = emojiPicker.style.display === 'block';
    emojiPicker.style.display = isVisible ? 'none' : 'block';
}

function insertEmoji(emoji) {
    const messageInput = document.getElementById('message-input');
    const currentValue = messageInput.value;
    const cursorPosition = messageInput.selectionStart;
    
    // Insert emoji at cursor position
    const newValue = currentValue.slice(0, cursorPosition) + emoji + currentValue.slice(cursorPosition);
    messageInput.value = newValue;
    
    // Move cursor after the emoji
    const newCursorPosition = cursorPosition + emoji.length;
    messageInput.setSelectionRange(newCursorPosition, newCursorPosition);
    
    // Focus back on input
    messageInput.focus();
    
    // Hide emoji picker
    document.getElementById('emoji-picker').style.display = 'none';
    
    // Trigger input event to update send button state
    messageInput.dispatchEvent(new Event('input'));
}

async function clearCurrentChat() {
    if (!confirm(`Are you sure you want to clear all conversations with ${botInfo[currentBot].name}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/delete_chats/${currentBot}`, {
            method: 'POST'
        });
        
        if (response.ok) {
            loadChatHistory();
            alert('Chat history cleared.');
        } else {
            alert('Error clearing chat history.');
        }
    } catch (error) {
        console.error('Error clearing chat:', error);
        alert('Error clearing chat history.');
    }
}

async function clearAllData() {
    if (!confirm('Are you sure you want to delete ALL your conversation data? This cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/clear_all', {
            method: 'POST'
        });
        
        if (response.ok) {
            loadChatHistory();
            alert('All conversation data has been deleted.');
        } else {
            alert('Error clearing data.');
        }
    } catch (error) {
        console.error('Error clearing all data:', error);
        alert('Error clearing data.');
    }
}