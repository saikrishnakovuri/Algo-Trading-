/**
 * Gemini API Handler Module
 * Refactored to communicate with the Python Backend API
 */

import { handleApiError, validateResponse } from "./utils.js";

// Backend API configuration
let backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
let initialized = false;

/**
 * Initializes the Gemini API client (now points to the backend)
 * @param {string} apiKey - Google Gemini API key (kept for compatibility, but managed by backend)
 * @param {string} model - Model name (kept for compatibility)
 * @returns {boolean} True if initialized
 */
export function initializeGemini(apiKey, model = "gemini-1.5-pro") {
  console.log(`✅ Gemini Assistant initialized via backend: ${backendUrl}`);
  initialized = true;
  return true;
}

/**
 * Sends code to the backend for analysis
 * @param {string} code - The code to analyze
 * @param {string} command - The operation (fix, optimize, explain, refactor)
 * @param {string} userPrompt - Additional user context/prompt
 * @param {string} fileName - Optional file name for context
 * @param {string} model - Model to use (managed by backend)
 * @returns {Promise<string>} Gemini's response
 */
export async function analyzeCode(
  code,
  command = "fix",
  userPrompt = "",
  fileName = "",
  model = "gemini-1.5-pro"
) {
  if (!initialized) {
    throw new Error("Gemini Assistant not initialized. Call initializeGemini first.");
  }

  try {
    console.log("🔄 Sending request to Backend API...");
    
    const response = await fetch(`${backendUrl}/api/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        code,
        command,
        fileName,
        context: userPrompt
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `Backend error: ${response.statusText}`);
    }

    const data = await response.json();
    const resultText = data.response;
    validateResponse(resultText);

    return resultText;
  } catch (error) {
    const errorMessage = handleApiError(error);
    throw new Error(errorMessage);
  }
}

/**
 * Sends a custom prompt to the backend
 * @param {string} prompt - The prompt to send
 * @param {string} model - Model to use
 * @returns {Promise<string>} Gemini's response
 */
export async function sendPrompt(prompt, model = "gemini-1.5-pro") {
  return analyzeCode(prompt, "explain", "", ""); // Reuse analyzeCode logic
}

/**
 * Performs a specific analysis command on code
 * @param {string} code - The code to analyze
 * @param {string} command - fix | optimize | explain | refactor
 * @param {string} fileName - Optional file name
 * @param {string} additionalContext - Optional additional context
 * @returns {Promise<string>} Analysis result
 */
export async function analyzeWithCommand(code, command, fileName = "", additionalContext = "") {
  return analyzeCode(code, command, additionalContext, fileName);
}

/**
 * Checks if Gemini Assistant is properly initialized
 * @returns {boolean} True if initialized
 */
export function isGeminiInitialized() {
  return initialized;
}

/**
 * Gets list of available models
 * @returns {Array} List of available models
 */
export function getAvailableModels() {
  return [
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.0-pro"
  ];
}

export default {
  initializeGemini,
  analyzeCode,
  sendPrompt,
  analyzeWithCommand,
  isGeminiInitialized,
  getAvailableModels
};
