/**
 * Travel Assistant - Main Application JavaScript
 * Handles language switching, preferences persistence, navigation
 */

// ===========================
// Configuration
// ===========================
const CONFIG = {
    API_BASE_URL: 'http://127.0.0.1:8000/api',
    STORAGE_KEYS: {
        LANGUAGE: 'travel_assistant_language',
        USER_TYPE: 'travel_assistant_user_type',
        USER_SESSION: 'travel_assistant_session'
    },
    DEFAULT_LANGUAGE: 'en',
    SUPPORTED_LANGUAGES: ['en', 'hi', 'kn']
};

// ===========================
// State Management
// ===========================
const state = {
    language: CONFIG.DEFAULT_LANGUAGE,
    userType: null,
    translations: {},
    isLoggedIn: false
};

// ===========================
// Translation System
// ===========================
async function loadTranslations() {
    try {
        const response = await fetch('translations.json');
        state.translations = await response.json();
        return true;
    } catch (error) {
        console.error('Failed to load translations:', error);
        return false;
    }
}

function t(key) {
    const langData = state.translations[state.language];
    return langData && langData[key] ? langData[key] : key;
}

function updatePageLanguage() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        el.textContent = t(key);
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        el.placeholder = t(key);
    });

    // Update document title
    document.title = t('appName');

    // Update language label
    const langLabel = document.getElementById('currentLangLabel');
    if (langLabel) {
        langLabel.textContent = state.language.toUpperCase();
    }

    // Update selected language in modal
    document.querySelectorAll('.language-option').forEach(opt => {
        opt.classList.toggle('selected', opt.dataset.lang === state.language);
    });
}

function setLanguage(lang) {
    if (!CONFIG.SUPPORTED_LANGUAGES.includes(lang)) {
        lang = CONFIG.DEFAULT_LANGUAGE;
    }
    state.language = lang;
    localStorage.setItem(CONFIG.STORAGE_KEYS.LANGUAGE, lang);
    updatePageLanguage();
    showToast(t('languageSaved'), 'success');
}

// ===========================
// User Type Selection
// ===========================
function setUserType(type) {
    state.userType = type;
    localStorage.setItem(CONFIG.STORAGE_KEYS.USER_TYPE, type);
    showToast(t('profileSaved'), 'success');

    // Navigate to chat page
    setTimeout(() => {
        window.location.href = `${type}.html`;
    }, 300);
}

function loadSavedPreferences() {
    // Load language
    const savedLang = localStorage.getItem(CONFIG.STORAGE_KEYS.LANGUAGE);
    if (savedLang && CONFIG.SUPPORTED_LANGUAGES.includes(savedLang)) {
        state.language = savedLang;
    }

    // Load user type
    const savedUserType = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_TYPE);
    if (savedUserType) {
        state.userType = savedUserType;
    }

    // Load session
    const savedSession = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_SESSION);
    if (savedSession) {
        try {
            const session = JSON.parse(savedSession);
            state.isLoggedIn = !!session.token;
        } catch (e) {
            state.isLoggedIn = false;
        }
    }
}

// ===========================
// Modal Management
// ===========================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay.active').forEach(modal => {
        modal.classList.remove('active');
    });
    document.body.style.overflow = '';
}

// ===========================
// Toast Notifications
// ===========================
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.innerHTML = `
    <span>${message}</span>
  `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastSlide 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ===========================
// Event Handlers
// ===========================
function setupEventListeners() {
    // Language button
    const languageBtn = document.getElementById('languageBtn');
    if (languageBtn) {
        languageBtn.addEventListener('click', () => openModal('languageModal'));
    }

    // Login button
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            if (state.isLoggedIn) {
                // Logout
                localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_SESSION);
                state.isLoggedIn = false;
                loginBtn.textContent = t('login');
                showToast('Logged out successfully', 'success');
            } else {
                openModal('loginModal');
            }
        });
    }

    // Language options
    document.querySelectorAll('.language-option').forEach(opt => {
        opt.addEventListener('click', () => {
            const lang = opt.dataset.lang;
            setLanguage(lang);
            closeModal('languageModal');
        });
    });

    // User type cards
    document.querySelectorAll('.user-card').forEach(card => {
        card.addEventListener('click', () => {
            const userType = card.dataset.userType;
            if (userType) {
                setUserType(userType);
            }
        });
    });

    // Close modal on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeAllModals();
            }
        });
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });

    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            // Simulate login (would connect to backend in production)
            const email = document.getElementById('email').value;
            if (email) {
                const session = { token: 'demo-token', email };
                localStorage.setItem(CONFIG.STORAGE_KEYS.USER_SESSION, JSON.stringify(session));
                state.isLoggedIn = true;
                closeModal('loginModal');
                const loginBtn = document.getElementById('loginBtn');
                if (loginBtn) loginBtn.textContent = t('logout');
                showToast('Logged in successfully', 'success');
            }
        });
    }
}

// ===========================
// Auto-redirect if user type saved
// ===========================
function checkAutoRedirect() {
    // Only auto-redirect from index page
    if (window.location.pathname.includes('index.html') ||
        window.location.pathname.endsWith('/') ||
        window.location.pathname.endsWith('/frontend/')) {

        const savedUserType = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_TYPE);
        const urlParams = new URLSearchParams(window.location.search);

        // Don't auto-redirect if user wants to change selection
        if (urlParams.get('change') === 'true') {
            localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_TYPE);
            return;
        }

        // Auto-redirect to saved user type page
        // Commented out for now - user may want to change selection
        // if (savedUserType && ['student', 'elderly', 'tourist'].includes(savedUserType)) {
        //   window.location.href = `${savedUserType}.html`;
        // }
    }
}

// ===========================
// Initialization
// ===========================
async function init() {
    // Load saved preferences first
    loadSavedPreferences();

    // Load translations
    await loadTranslations();

    // Update page with current language
    updatePageLanguage();

    // Setup event listeners
    setupEventListeners();

    // Update login button state
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn && state.isLoggedIn) {
        loginBtn.textContent = t('logout');
    }

    // Check for auto-redirect
    checkAutoRedirect();

    console.log('Travel Assistant initialized');
}

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', init);

// Export for use in other modules
window.TravelAssistant = {
    CONFIG,
    state,
    t,
    setLanguage,
    showToast,
    openModal,
    closeModal
};
