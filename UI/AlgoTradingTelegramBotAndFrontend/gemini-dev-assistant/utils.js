/**
 * Utility functions for the Gemini Dev Assistant
 * Includes validation, formatting, and error handling helpers
 */

/**
 * Validates that the Gemini API key is configured
 * @param {string} apiKey - The API key to validate
 * @returns {boolean} True if API key is valid, throws error otherwise
 */
export function validateApiKey(apiKey) {
  if (!apiKey) {
    throw new Error(
      "❌ GEMINI_API_KEY is not configured!\n" +
      "1. Get your API key from: https://aistudio.google.com/app/apikeys\n" +
      "2. Copy .env.example to .env\n" +
      "3. Add your API key to the .env file"
    );
  }
  if (apiKey === "your_api_key_here") {
    throw new Error(
      "❌ GEMINI_API_KEY is not set correctly in .env file!\n" +
      "Please replace 'your_api_key_here' with your actual API key"
    );
  }
  return true;
}

/**
 * Validates file type to prevent sending binary files
 * @param {string} filename - The name of the file
 * @returns {boolean} True if file is a text file type
 */
export function isValidFileType(filename) {
  const validExtensions = [
    ".js", ".jsx", ".ts", ".tsx", ".py", ".java", ".cpp", ".c", ".h",
    ".cs", ".php", ".rb", ".go", ".rs", ".kotlin", ".swift", ".m",
    ".scala", ".groovy", ".sh", ".bash", ".sql", ".html", ".css",
    ".scss", ".sass", ".less", ".json", ".xml", ".yaml", ".yml",
    ".toml", ".ini", ".env", ".txt", ".md", ".vue", ".lua", ".perl"
  ];

  const extension = filename.toLowerCase().substring(filename.lastIndexOf("."));
  return validExtensions.includes(extension);
}

/**
 * Formats file content for display with line numbers
 * @param {string} content - The file content
 * @param {number} maxLines - Maximum lines to show
 * @returns {string} Formatted content with line numbers
 */
export function formatFileContent(content, maxLines = 50) {
  const lines = content.split("\n");
  
  if (lines.length > maxLines) {
    const truncatedLines = lines.slice(0, maxLines);
    const lineNumbers = truncatedLines
      .map((line, i) => `${String(i + 1).padStart(3, " ")} | ${line}`)
      .join("\n");
    return (
      lineNumbers +
      `\n\n... (${lines.length - maxLines} more lines, showing first ${maxLines})`
    );
  }

  return lines
    .map((line, i) => `${String(i + 1).padStart(3, " ")} | ${line}`)
    .join("\n");
}

/**
 * Truncates long prompts for logging
 * @param {string} prompt - The prompt to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated prompt
 */
export function truncatePrompt(prompt, maxLength = 100) {
  if (prompt.length > maxLength) {
    return prompt.substring(0, maxLength) + "...";
  }
  return prompt;
}

/**
 * Creates a context-aware system prompt for Gemini
 * @param {string} command - The operation (fix, optimize, explain, refactor)
 * @returns {string} The system prompt
 */
export function getSystemPrompt(command) {
  const prompts = {
    fix: "You are an expert code reviewer. Analyze the provided code and identify bugs, issues, and fix them. Return only the corrected code with brief explanation of changes.",
    optimize: "You are a performance optimization expert. Analyze the provided code and suggest optimizations for speed, memory usage, and efficiency. Return the optimized code with explanation of improvements.",
    explain: "You are a code documentation expert. Explain the provided code in clear, simple terms. Break down what it does, how it works, and the logic behind it.",
    refactor: "You are a code quality expert. Refactor the provided code to follow best practices, improve readability, and enhance maintainability. Return the refactored code with explanation of changes."
  };

  return prompts[command] || prompts.fix;
}

/**
 * Maps user-friendly command names to internal command names
 * @param {string} input - User input
 * @returns {string} Normalized command name
 */
export function normalizeCommand(input) {
  const commands = {
    fix: ["fix", "debug", "bug", "repair"],
    optimize: ["optimize", "performance", "improve", "speed"],
    explain: ["explain", "analyze", "understand", "describe"],
    refactor: ["refactor", "clean", "improve", "reorganize"]
  };

  const lowerInput = input.toLowerCase().trim();

  for (const [cmd, aliases] of Object.entries(commands)) {
    if (aliases.includes(lowerInput)) {
      return cmd;
    }
  }

  return "fix"; // Default to fix command
}

/**
 * Handles API rate limiting errors gracefully
 * @param {Error} error - The error object
 * @returns {string} Human-readable error message
 */
export function handleApiError(error) {
  const message = error.message || "";

  if (message.includes("429") || message.includes("RESOURCE_EXHAUSTED")) {
    return "⏸️  Rate limit reached. Please wait a moment and try again.";
  }
  if (message.includes("401") || message.includes("UNAUTHENTICATED")) {
    return "❌ Invalid API key. Please check your GEMINI_API_KEY in the .env file.";
  }
  if (message.includes("403") || message.includes("PERMISSION_DENIED")) {
    return "❌ Permission denied. Check if your API key has access to Gemini.";
  }
  if (message.includes("404")) {
    return "❌ Model not found. Please check the GEMINI_MODEL in .env file.";
  }
  if (message.includes("500")) {
    return "❌ Gemini API server error. Please try again later.";
  }

  return `❌ API Error: ${message}`;
}

/**
 * Validates that response is not empty
 * @param {string} response - The response text
 * @returns {string} Validated response or error message
 */
export function validateResponse(response) {
  if (!response || response.trim() === "") {
    throw new Error("Empty response from Gemini API");
  }
  return response;
}

export default {
  validateApiKey,
  isValidFileType,
  formatFileContent,
  truncatePrompt,
  getSystemPrompt,
  normalizeCommand,
  handleApiError,
  validateResponse
};
