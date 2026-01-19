/**
 * Chat functionality for Travel Assistant
 * Handles voice recording, transcription, translation, and chat UI
 */

// ===========================
// Chat State
// ===========================
const chatState = {
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    messages: [],
    userType: null,
    isProcessing: false
};

// ===========================
// Audio Recording
// ===========================
async function initializeAudioRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        chatState.mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'audio/webm;codecs=opus'
        });

        chatState.mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                chatState.audioChunks.push(event.data);
            }
        };

        chatState.mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(chatState.audioChunks, { type: 'audio/webm' });
            chatState.audioChunks = [];
            await processAudioRecording(audioBlob);
        };

        return true;
    } catch (error) {
        console.error('Microphone access denied:', error);
        if (window.TravelAssistant) {
            window.TravelAssistant.showToast(
                window.TravelAssistant.t('microphonePermission'),
                'error'
            );
        }
        return false;
    }
}

function startRecording() {
    if (!chatState.mediaRecorder) {
        initializeAudioRecording().then(success => {
            if (success) startRecording();
        });
        return;
    }

    chatState.audioChunks = [];
    chatState.mediaRecorder.start();
    chatState.isRecording = true;
    updateRecordingUI(true);
}

function stopRecording() {
    if (chatState.mediaRecorder && chatState.isRecording) {
        chatState.mediaRecorder.stop();
        chatState.isRecording = false;
        updateRecordingUI(false);
    }
}

function toggleRecording() {
    if (chatState.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

function updateRecordingUI(isRecording) {
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceBtnLarge = document.getElementById('voiceBtnLarge');
    const statusText = document.getElementById('recordingStatus');

    [voiceBtn, voiceBtnLarge].forEach(btn => {
        if (btn) {
            btn.classList.toggle('recording', isRecording);
            btn.innerHTML = isRecording ? '⏹️' : '🎤';
        }
    });

    if (statusText) {
        statusText.textContent = isRecording ?
            (window.TravelAssistant ? window.TravelAssistant.t('recording') : 'Recording...') : '';
    }
}

// ===========================
// Audio Processing
// ===========================
async function processAudioRecording(audioBlob) {
    setProcessingState(true);

    try {
        // Convert blob to base64
        const base64Audio = await blobToBase64(audioBlob);

        // Get current language
        const language = window.TravelAssistant?.state?.language || 'en';

        // Send to transcription API
        const transcription = await transcribeAudio(base64Audio, language);

        if (transcription.text) {
            // Put transcribed text in input field
            const chatInput = document.getElementById('chatInput');
            if (chatInput) {
                chatInput.value = transcription.text;
            }

            // Optionally auto-send
            // await sendMessage(transcription.text);
        } else if (transcription.error) {
            window.TravelAssistant?.showToast(transcription.error, 'error');
        }
    } catch (error) {
        console.error('Audio processing error:', error);
        window.TravelAssistant?.showToast(
            window.TravelAssistant?.t('errorOccurred') || 'Error processing audio',
            'error'
        );
    } finally {
        setProcessingState(false);
    }
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const base64 = reader.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

// ===========================
// API Calls
// ===========================
async function transcribeAudio(base64Audio, language) {
    // Call the dedicated /transcribe endpoint for audio-to-text
    const apiUrl = 'http://127.0.0.1:8000';

    try {
        console.log('[TRANSCRIBE] Sending audio to backend for transcription...');
        const response = await fetch(`${apiUrl}/transcribe`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                audio: base64Audio,
                language: language
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        console.log('[TRANSCRIBE] Result:', result);
        return result;
    } catch (error) {
        console.error('Transcription API error:', error);
        return { text: '', error: 'Transcription failed. Please try again.' };
    }
}

async function translateText(text, sourceLanguage, targetLanguage) {
    const apiUrl = window.TravelAssistant?.CONFIG?.API_BASE_URL || 'http://127.0.0.1:8000/api';

    try {
        const response = await fetch(`${apiUrl}/translate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                source_language: sourceLanguage,
                target_language: targetLanguage
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Translation API error:', error);
        return { translated_text: text, error: 'Translation failed' };
    }
}

async function sendToVoiceQuery(text, userType) {
    const apiUrl = 'http://127.0.0.1:8000';
    const language = window.TravelAssistant?.state?.language || 'en';

    try {
        // First translate if not in English
        let queryText = text;
        if (language !== 'en') {
            const translation = await translateText(text, language, 'en');
            if (translation.translated_text) {
                queryText = translation.translated_text;
            }
        }

        // Get or create persistent session ID
        if (!chatState.sessionId) {
            chatState.sessionId = `web-${Date.now()}`;
        }

        // Parse origin and destination from message if present
        let origin = null;
        let destination = null;

        // Simple parsing for "from X to Y" pattern
        const fromToMatch = queryText.match(/from\s+(.+?)\s+to\s+(.+?)(?:\s*[.,]|$)/i);
        if (fromToMatch) {
            origin = fromToMatch[1].trim();
            destination = fromToMatch[2].trim();
        }

        const response = await fetch(`${apiUrl}/voice-query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: queryText, // Backend now expects text directly (no audio processing)
                user_type: userType,
                language: language,
                city: 'Bengaluru',
                session_id: chatState.sessionId,
                home: origin,
                destination: destination
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Voice query API error:', error);
        throw error;
    }
}

// ===========================
// Chat UI
// ===========================
function addMessage(text, isUser = false) {
    const chatBody = document.getElementById('chatBody');
    if (!chatBody) return;

    const message = {
        id: Date.now(),
        text,
        isUser,
        timestamp: new Date()
    };

    chatState.messages.push(message);

    const messageEl = document.createElement('div');
    messageEl.className = `chat-message chat-message--${isUser ? 'user' : 'bot'}`;
    messageEl.innerHTML = `
    <div class="chat-message__avatar">${isUser ? '👤' : '🤖'}</div>
    <div class="chat-message__content">
      <p class="chat-message__text">${escapeHtml(text)}</p>
    </div>
  `;

    chatBody.appendChild(messageEl);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function addTypingIndicator() {
    const chatBody = document.getElementById('chatBody');
    if (!chatBody) return;

    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'chat-message chat-message--bot';
    indicator.innerHTML = `
    <div class="chat-message__avatar">🤖</div>
    <div class="chat-message__content">
      <div class="loading-dots">
        <span></span><span></span><span></span>
      </div>
    </div>
  `;

    chatBody.appendChild(indicator);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

function setProcessingState(isProcessing) {
    chatState.isProcessing = isProcessing;

    const sendBtn = document.getElementById('sendBtn');
    const voiceBtn = document.getElementById('voiceBtn');
    const chatInput = document.getElementById('chatInput');

    [sendBtn, voiceBtn].forEach(btn => {
        if (btn) btn.disabled = isProcessing;
    });

    if (chatInput) chatInput.disabled = isProcessing;

    if (isProcessing) {
        addTypingIndicator();
    } else {
        removeTypingIndicator();
    }
}

async function sendMessage(text = null) {
    const chatInput = document.getElementById('chatInput');
    const messageText = text || (chatInput ? chatInput.value.trim() : '');

    if (!messageText || chatState.isProcessing) return;

    // Clear input
    if (chatInput) chatInput.value = '';

    // Add user message
    addMessage(messageText, true);

    // Process with backend
    setProcessingState(true);

    try {
        const response = await sendToVoiceQuery(messageText, chatState.userType);
        console.log('Voice query response:', response);

        // Format response
        let botResponse = '';

        // Check if this is a final selection response (user chose cheapest/fastest)
        const isSelectionResponse = response.selected_option ||
            (response.intent && response.intent.intent === 'select_option');

        if (response.decision) {
            botResponse = response.decision;
        }
        if (response.explanation) {
            botResponse += `\n\n${response.explanation}`;
        }

        // Only show follow-up question if this is NOT a final selection
        if (response.follow_up_question && !isSelectionResponse) {
            botResponse += `\n\n${response.follow_up_question}`;
        } else if (isSelectionResponse) {
            // Add a helpful closing message for selection responses
            botResponse += '\n\nHave a safe journey! 🚌';
        }

        // Translate response if needed
        const language = window.TravelAssistant?.state?.language || 'en';
        if (language !== 'en' && botResponse) {
            const translation = await translateText(botResponse, 'en', language);
            if (translation.translated_text) {
                botResponse = translation.translated_text;
            }
        }

        if (botResponse) {
            addMessage(botResponse, false);
        } else {
            addMessage('I received your message. How can I help you further?', false);
        }
    } catch (error) {
        console.error('Send message error:', error);
        addMessage(
            window.TravelAssistant?.t('errorOccurred') || 'Sorry, something went wrong. Please try again.',
            false
        );
    } finally {
        setProcessingState(false);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===========================
// Initialization
// ===========================
function initChat(userType) {
    chatState.userType = userType;

    // Setup voice button
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceBtnLarge = document.getElementById('voiceBtnLarge');

    [voiceBtn, voiceBtnLarge].forEach(btn => {
        if (btn) {
            btn.addEventListener('click', toggleRecording);
        }
    });

    // Setup send button
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', () => sendMessage());
    }

    // Setup input field
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Setup back button
    const backBtn = document.getElementById('backBtn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            window.location.href = 'index.html?change=true';
        });
    }

    // Wait for TravelAssistant to be ready with translations, then show greeting
    const showGreeting = () => {
        const greetings = {
            student: {
                en: "Hi! I'll help you find the best routes for your daily commute.",
                hi: "नमस्ते! मैं आपकी दैनिक यात्रा के लिए सबसे अच्छे रास्ते खोजने में मदद करूंगा।",
                kn: "ನಮಸ್ಕಾರ! ನಿಮ್ಮ ದೈನಂದಿನ ಪ್ರಯಾಣಕ್ಕೆ ಉತ್ತಮ ಮಾರ್ಗಗಳನ್ನು ಹುಡುಕಲು ನಾನು ಸಹಾಯ ಮಾಡುತ್ತೇನೆ."
            },
            elderly: {
                en: "Hello! I'm here to help you travel safely and comfortably.",
                hi: "नमस्कार! मैं आपको सुरक्षित और आरामदायक यात्रा में मदद करने के लिए यहां हूं।",
                kn: "ನಮಸ್ಕಾರ! ಸುರಕ್ಷಿತ ಮತ್ತು ಆರಾಮದಾಯಕ ಪ್ರಯಾಣದಲ್ಲಿ ನಿಮಗೆ ಸಹಾಯ ಮಾಡಲು ನಾನು ಇಲ್ಲಿದ್ದೇನೆ."
            },
            tourist: {
                en: "Welcome to the city! Let me help you explore amazing places.",
                hi: "शहर में आपका स्वागत है! मुझे अद्भुत स्थानों की खोज में आपकी मदद करने दीजिए।",
                kn: "ನಗರಕ್ಕೆ ಸ್ವಾಗತ! ಅದ್ಭುತ ಸ್ಥಳಗಳನ್ನು ಅನ್ವೇಷಿಸಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ."
            }
        };

        const lang = window.TravelAssistant?.state?.language || 'en';
        const greeting = greetings[userType]?.[lang] ||
            window.TravelAssistant?.t(`${userType}Greeting`) ||
            `Hello! I'm your ${userType} travel assistant. How can I help you today?`;

        addMessage(greeting, false);

        // Update placeholder with translation
        if (chatInput && window.TravelAssistant) {
            chatInput.placeholder = window.TravelAssistant.t('typeMessage');
        }
    };

    // Wait a bit for translations to load, then show greeting
    setTimeout(showGreeting, 800);

    // Initialize audio on first interaction
    document.body.addEventListener('click', () => {
        if (!chatState.mediaRecorder) {
            initializeAudioRecording();
        }
    }, { once: true });
}

// ===========================
// Switch to text input (for elderly)
// ===========================
function showTextInput() {
    const voiceFirst = document.getElementById('voiceFirstContainer');
    const textInput = document.getElementById('textInputContainer');

    if (voiceFirst) voiceFirst.classList.add('hidden');
    if (textInput) textInput.classList.remove('hidden');
}

// Export for use
window.ChatAssistant = {
    initChat,
    sendMessage,
    toggleRecording,
    showTextInput
};
