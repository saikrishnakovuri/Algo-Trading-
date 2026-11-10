/*
 * Gemini service for the VS Code extension
 * Refactored to communicate with the Python Backend API
 */

// We don't need the SDK here anymore
let initialized = false;
let backendUrl = 'http://localhost:8000'; // Default backend URL

/**
 * Initialize the Gemini client (now points to the backend)
 * Can be called multiple times; re-initializes only if needed.
 */
async function initialize(apiKey, model = 'gemini-1.5-pro-latest') {
    // In the new architecture, the backend handles the API key,
    // but we keep this function signature for compatibility with extension.js
    console.log('Gemini service initialized via backend');
    initialized = true;
    return true;
}

/**
 * Send code + command to Backend and return the text response
 */
async function analyzeWithCommand(code, command = 'fix', fileName = '', additionalContext = '') {
    if (!initialized) {
        throw new Error('Gemini service not initialized. Call initialize() first.');
    }

    try {
        const response = await fetch(`${backendUrl}/api/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: code,
                command: command,
                fileName: fileName,
                context: additionalContext
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Backend error: ${response.statusText}`);
        }

        const data = await response.json();
        const text = data.response;

        if (!text || text.trim() === '') {
            throw new Error('Empty response from Gemini API via Backend');
        }

        return text;
    } catch (err) {
        const msg = String(err.message || err);
        if (msg.includes('401') || msg.includes('UNAUTHENTICATED')) {
            throw new Error('Invalid API key or authentication error (reported by backend)');
        }
        if (msg.includes('429') || msg.includes('RATE_LIMIT')) {
            throw new Error('Rate limit exceeded (reported by backend)');
        }
        throw new Error('Backend/Gemini API error: ' + msg);
    }
}

module.exports = { initialize, analyzeWithCommand };
