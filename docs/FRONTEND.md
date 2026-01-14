# Frontend Documentation

## Overview

The AI Travel Assistant frontend is a **voice-first, mobile-friendly web application** with three distinct user interfaces tailored for students, elderly users, and tourists.

**Base URL:** `http://localhost:5500`

---

## Pages

### 1. Landing Page (`index.html`)

Entry point with user type selection.

**Features:**
- Three user type cards (Student, Elderly, Tourist)
- Animated gradient background
- Quick access to each mode

---

### 2. Student Mode (`student.html`)

Optimized for budget-conscious travel.

**UI Elements:**
- Chat interface for natural language queries
- Voice input button (microphone)
- Route cards showing cheapest vs fastest
- Deep links to Ola, Uber, Rapido

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
- Step-by-step directions
- Cab-first recommendations (safety)
- Emergency contact button

---

### 4. Tourist Mode (`tourist.html`)

AI-powered itinerary planning.

**Features:**
- Destination search
- Sightseeing mode with AI suggestions
- Multi-day itinerary planning
- Nearby attractions

---

## JavaScript Architecture

```
frontend/
├── index.html          # Landing page
├── student.html        # Student interface
├── elderly.html        # Elderly interface
├── tourist.html        # Tourist interface
├── js/
│   ├── chat.js         # Chat UI logic
│   ├── voice.js        # Speech recognition
│   └── api.js          # Backend API calls
├── css/
│   └── style.css       # Global styles
└── assets/
    └── icons/          # UI icons
```

---

## API Integration

### Sending Queries

```javascript
async function sendQuery(text, userType) {
    const response = await fetch('http://localhost:8000/voice-query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text: text,
            user_type: userType,
            language: 'en'
        })
    });
    return response.json();
}
```

### Voice Input

Uses Web Speech API for voice recognition:

```javascript
const recognition = new webkitSpeechRecognition();
recognition.continuous = false;
recognition.interimResults = true;

recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    sendQuery(transcript, 'student');
};
```

---

## Response Display

### Route Cards

Each route option is displayed as a card:

```html
<div class="route-card cheapest">
    <div class="route-header">
        <span class="mode-icon">🚌</span>
        <span class="mode-name">Bus V-500A</span>
    </div>
    <div class="route-details">
        <span class="cost">₹25</span>
        <span class="time">35 mins</span>
    </div>
    <div class="steps">
        1. 🚶 Walk to Hebbal Bus Stop (~5 min)
        2. 🚌 Take Bus V-500A towards Majestic (~25 min)
        3. 🚶 Walk to destination (~5 min)
    </div>
</div>
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
