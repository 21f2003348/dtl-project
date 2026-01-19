# Frontend Documentation

## Overview

The AI Travel Assistant frontend is a **voice-first, mobile-friendly web application** with three distinct user interfaces tailored for students, elderly users, and tourists.

**Base URL:** `http://localhost:5500`

---

## User Type Experiences

| User Type | Page | Priority | UI Focus |
|-----------|------|----------|----------|
| **Student** | `student.html` | Cheap & Fast | All route options with cost/time comparison |
| **Elderly** | `elderly.html` | Comfort & Safety | Comfort-ranked options, large text, simple UI |
| **Tourist** | `tourist.html` | Discovery | AI conversational recommendations |

---

## Pages

### 1. Landing Page (`index.html`)

Entry point with user type selection.

**Features:**
- Three user type cards (Student, Elderly, Tourist)
- Animated gradient background
- Language selection (English, Hindi, Kannada)
- Quick access to each mode

---

### 2. Student Mode (`student.html`)

Optimized for budget-conscious travel.

**UI Elements:**
- Chat interface for natural language queries
- Voice input button (microphone)
- Route cards showing cheapest vs fastest
- **All Options list** for full transparency
- Deep links to Ola, Uber, Rapido

**Response Format:**
```
From Hebbal to Majestic:

🚌 **Cheapest**: ₹25 (35 mins) - Bus
⚡ **Fastest**: ₹132 (21 mins) - Auto

📋 **All Options:**
  • Bus: ₹25 (35 mins)
  • Metro: ₹40 (28 mins)
  • Auto: ₹132 (21 mins)
```

**Sample Queries:**
- "How do I get to Majestic from Hebbal?"
- "Cheapest way to RVCE"
- "Bus to Electronic City"

---

### 3. Elderly Mode (`elderly.html`)

Accessibility-focused with larger text and simpler UI.

**Features:**
- Large, high-contrast buttons
- Voice guidance
- **Comfort-ranked options** (most comfortable first)
- Comfort scores displayed (0-100+)
- Cab-first recommendations for safety
- Emergency contact button

**Response Format:**
```
Route options ranked by comfort:

🏆 Cab - ₹158 (29 mins) [AC] - Comfort: 115/100
Auto - ₹165 (26 mins) - Comfort: 100/100
Metro - ₹29 (26 mins) [AC] - Comfort: 70/100
Bus - ₹25 (46 mins) - Comfort: 35/100

We recommend a Cab for maximum comfort and door-to-door service.
```

**Comfort Score Factors:**
- AC availability (+20)
- Guaranteed seating (+15)
- Door-to-door service (+25)
- Minimal walking (+10-20)
- Fewer transfers (+10 each)

---

### 4. Tourist Mode (`tourist.html`)

AI-powered conversational itinerary planning.

**Features:**
- Natural conversation for location input
- Preference questions (travel style, group, interests)
- AI-generated place recommendations
- 50km radius filtering
- Multi-day itinerary suggestions

**Conversation Flow:**
```
User: "I'm in Hampi for 3 days"

Bot: "Great! You're exploring **Hampi** for **3 days**! 🎉
      What kind of traveler are you?"
      
      [Adventurer] [Culture Enthusiast] [Relaxed Explorer] [Foodie]

User: [clicks "Culture Enthusiast"]

Bot: "Here are my top recommendations:

      📍 Virupaksha Temple (0km)
         Ancient temple dedicated to Lord Shiva...
         ⏱️ 2-3 hours | 💰 ₹40
         
      📍 Vittala Temple Complex (3km)
         Famous for the iconic Stone Chariot...
         ⏱️ 3-4 hours | 💰 ₹40"
```

---

## JavaScript Architecture

```
frontend/
├── index.html          # Landing page
├── student.html        # Student interface
├── elderly.html        # Elderly interface
├── tourist.html        # Tourist interface
├── app.js              # Global app logic, translations
├── chat.js             # Chat UI, voice, API integration
├── styles.css          # Global styles
└── translations.json   # Multi-language support
```

---

## Chat Interface (`chat.js`)

### Key Functions

```javascript
// Initialize chat for specific user type
window.ChatAssistant.initChat('student');

// Send text message
window.ChatAssistant.sendMessage('Hebbal to Majestic');

// Toggle voice recording
window.ChatAssistant.toggleRecording();
```

### Response Processing

The chat displays responses based on user type:

```javascript
// Format response for display
if (response.decision) {
    botResponse = response.decision;
}
if (response.explanation) {
    botResponse += `\n\n${response.explanation}`;
}
if (response.follow_up_question) {
    botResponse += `\n\n${response.follow_up_question}`;
}
```

---

## API Integration

### Sending Queries

```javascript
async function sendToVoiceQuery(text, userType) {
    const response = await fetch('http://127.0.0.1:8000/voice-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            user_type: userType,  // 'student' | 'elderly' | 'tourist'
            language: 'en',
            city: 'Bengaluru',
            session_id: sessionId
        })
    });
    return response.json();
}
```

### Voice Input

Uses Web Speech API and backend transcription:

```javascript
// Record audio
const mediaRecorder = new MediaRecorder(stream);
mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);

// Transcribe via backend
const result = await fetch('/transcribe', {
    method: 'POST',
    body: JSON.stringify({ audio: base64Audio, language: 'en' })
});
```

---

## Multi-Language Support

### Available Languages

| Code | Language | Native |
|------|----------|--------|
| `en` | English | English |
| `hi` | Hindi | हिंदी |
| `kn` | Kannada | ಕನ್ನಡ |

### Usage

```javascript
// Get translated string
const text = window.TravelAssistant.t('welcome');

// Set language
window.TravelAssistant.setLanguage('kn');
```

---

## Styling

### Design Principles

1. **Mobile-first**: Optimized for smartphones
2. **Dark mode**: Easy on the eyes
3. **High contrast**: Accessible text
4. **Glassmorphism**: Modern UI aesthetics
5. **Animations**: Smooth transitions

### Color Palette

```css
:root {
    --primary: #6366f1;      /* Indigo */
    --secondary: #8b5cf6;    /* Purple */
    --background: #0f172a;   /* Dark blue */
    --surface: #1e293b;      /* Slate */
    --text: #f1f5f9;         /* Light gray */
    --success: #22c55e;      /* Green */
    --warning: #f59e0b;      /* Amber */
}
```

---

## Running the Frontend

```bash
cd frontend
python -m http.server 5500
```

Then open: `http://localhost:5500`

---

## Browser Compatibility

| Browser | Supported | Notes |
|---------|-----------|-------|
| Chrome | ✅ Full | Best experience |
| Firefox | ✅ Full | Speech API limited |
| Safari | ⚠️ Partial | WebKit prefix needed |
| Edge | ✅ Full | Chromium-based |
