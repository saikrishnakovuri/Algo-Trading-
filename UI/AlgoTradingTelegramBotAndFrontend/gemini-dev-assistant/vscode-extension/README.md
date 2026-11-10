# Gemini Code Assistant (VS Code Extension)

This extension converts selected code into requests to Google Gemini models (e.g., `gemini-1.5-pro-latest`) for: Explain, Fix Bugs, Optimize, and Refactor.

## Files
- `extension.js` - VS Code extension entry (commands, webview UI)
- `geminiService.js` - Gemini API integration
- `package.json` - Extension manifest and contributes (commands, menus, configuration)

## Setup (developer)
1. Open this folder (`vscode-extension`) in VS Code.
2. Install dependencies:

```bash
npm install
```

3. Configure API key:
- Set `gemini.apiKey` in Settings (File → Preferences → Settings) OR
- Set environment variable `GEMINI_API_KEY`.

4. Run extension in debug (F5):
- Press `F5` to launch Extension Development Host
- Open a file in the dev host, select code, right-click → Gemini menu or use the Command Palette

## Notes
- The extension uses the official `@google/generative-ai` SDK; network access and a valid API key are required.
- The extension shows results in a webview panel; for fix/refactor/optimize results you can click "Apply Changes" to replace the selected code.

## Troubleshooting
- If the extension shows "API key not configured", add `gemini.apiKey` in settings or set `GEMINI_API_KEY`.
- If you encounter rate limits, try changing `gemini.model` to a cheaper/faster variant.

## Security
- Do not commit your API key to version control. Use workspace settings or environment variables.

Enjoy! 🎉
